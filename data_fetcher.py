"""
数据获取模块
包括交易数据（K线及技术指标）和账户数据的获取
"""
import requests
import talib
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import time
import hmac
import hashlib
from urllib.parse import urlencode
import os


class DataFetcher:
    """数据获取类，负责获取市场数据和账户数据"""
    
    def __init__(self, exchange_config: Dict, skip_latest_candle: bool = False):
        """
        初始化数据获取器
        
        Args:
            exchange_config: 交易所配置信息
            skip_latest_candle: 是否跳过最新一根K线进行计算与输出
        """
        # 优先从环境变量读取密钥，其次从配置读取
        api_key_env = exchange_config.get('api_key_env', 'EXCHANGE_API_KEY')
        api_secret_env = exchange_config.get('api_secret_env', 'EXCHANGE_API_SECRET')
        self.api_key = os.getenv(api_key_env) or exchange_config.get('api_key')
        self.api_secret = os.getenv(api_secret_env) or exchange_config.get('api_secret')
        self.testnet = exchange_config.get('testnet', True)
        
        # 根据是否测试网设置基础URL（此处以币安为例）
        if self.testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
        
        # 数据计算选项
        self.skip_latest_candle = bool(skip_latest_candle)

    # ======================
    # 认证/签名相关工具方法
    # ======================
    def _generate_signature(self, params: Dict) -> str:
        """生成HMAC SHA256签名"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _send_signed_request(self, method: str, endpoint: str, params: Dict) -> Dict:
        """发送需要签名的请求（期货USDT-M，带重试机制）"""
        if not self.api_key or not self.api_secret:
            print("缺少交易所API凭证，无法调用签名接口。请设置环境变量 EXCHANGE_API_KEY 与 EXCHANGE_API_SECRET。")
            return {"code": -1, "msg": "MISSING_API_CREDENTIALS"}
        
        # 保存原始参数，避免重试时参数被污染
        original_params = params.copy() if params else {}
        # 默认添加较大的 recvWindow 提高容错
        if 'recvWindow' not in original_params:
            original_params['recvWindow'] = 5000
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 每次重试使用原始参数的新副本
                request_params = original_params.copy()
                request_params['timestamp'] = int(time.time() * 1000)
                request_params['signature'] = self._generate_signature(request_params)

                headers = {
                    'X-MBX-APIKEY': self.api_key
                }

                url = f"{self.base_url}{endpoint}"
                
                if method == 'GET':
                    r = requests.get(url, params=request_params, headers=headers, timeout=30)
                elif method == 'POST':
                    r = requests.post(url, params=request_params, headers=headers, timeout=30)
                elif method == 'DELETE':
                    r = requests.delete(url, params=request_params, headers=headers, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                    
                r.raise_for_status()
                return r.json()
                
            except requests.exceptions.Timeout:
                print(f"签名请求超时 [{method} {endpoint}] (尝试 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return {"code": -1, "msg": "REQUEST_TIMEOUT", "error": "请求超时"}
                    
            except requests.exceptions.RequestException as e:
                print(f"签名请求网络错误 [{method} {endpoint}] (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    try:
                        return r.json()
                    except Exception:
                        return {"code": -1, "msg": "NETWORK_ERROR", "error": str(e)}
                        
            except Exception as e:
                print(f"签名请求失败 [{method} {endpoint}]: {e}")
                return {"code": -1, "msg": "UNKNOWN_ERROR", "error": str(e)}
        
        return {"code": -1, "msg": "MAX_RETRIES_EXCEEDED"}
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Dict]:
        """
        获取K线数据（带重试机制）
        
        Args:
            symbol: 交易对符号，如 'BTCUSDT'
            interval: K线间隔，如 '3m', '4h'
            limit: 获取的K线数量
            
        Returns:
            K线数据列表
        """
        endpoint = f"{self.base_url}/fapi/v1/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        # 重试配置
        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries):
            try:
                # 增加超时时间到30秒
                response = requests.get(endpoint, params=params, timeout=30)
                response.raise_for_status()
                klines = response.json()
                
                # 转换为更易用的格式
                processed_klines = []
                for k in klines:
                    processed_klines.append({
                        'open_time': k[0],
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5]),
                        'close_time': k[6],
                    })
                
                return processed_klines
                
            except requests.exceptions.Timeout:
                print(f"获取K线数据超时 (尝试 {attempt + 1}/{max_retries}): {symbol} {interval}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"获取K线数据最终失败: {symbol} {interval} - 超时")
                    return []
                    
            except requests.exceptions.RequestException as e:
                print(f"获取K线数据网络错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"获取K线数据最终失败: {symbol} {interval}")
                    return []
                    
            except Exception as e:
                print(f"获取K线数据异常: {e}")
                return []
        
        return []
    
    def calculate_indicators(self, klines: List[Dict], is_short_term: bool = True) -> Dict:
        """
        计算技术指标
        
        Args:
            klines: K线数据列表
            is_short_term: 是否为短期指标
            
        Returns:
            包含各种技术指标的字典
        """
        if not klines or len(klines) < 50:
            return {}
        
        # 提取收盘价、最高价、最低价
        closes = np.array([k['close'] for k in klines])
        highs = np.array([k['high'] for k in klines])
        lows = np.array([k['low'] for k in klines])
        volumes = np.array([k['volume'] for k in klines])
        
        indicators = {}
        
        try:
            # 计算EMA
            ema_20 = talib.EMA(closes, timeperiod=20)
            indicators['ema_20'] = ema_20
            
            if not is_short_term:
                # 长期指标还需要50周期EMA
                ema_50 = talib.EMA(closes, timeperiod=50)
                indicators['ema_50'] = ema_50
            
            # 计算MACD
            macd, macdsignal, macdhist = talib.MACD(closes, 
                                                     fastperiod=12, 
                                                     slowperiod=26, 
                                                     signalperiod=9)
            indicators['macd'] = macd
            indicators['macd_signal'] = macdsignal
            indicators['macd_hist'] = macdhist
            
            # 计算RSI
            rsi_7 = talib.RSI(closes, timeperiod=7)
            rsi_14 = talib.RSI(closes, timeperiod=14)
            indicators['rsi_7'] = rsi_7
            indicators['rsi_14'] = rsi_14
            
            if not is_short_term:
                # 长期指标计算ATR
                atr_3 = talib.ATR(highs, lows, closes, timeperiod=3)
                atr_14 = talib.ATR(highs, lows, closes, timeperiod=14)
                indicators['atr_3'] = atr_3
                indicators['atr_14'] = atr_14
                indicators['volumes'] = volumes
            
            return indicators
            
        except Exception as e:
            print(f"计算技术指标失败: {e}")
            return {}
    
    def get_open_interest_and_funding(self, symbol: str) -> Dict:
        """
        获取持仓量和资金费率（带重试机制）
        
        Args:
            symbol: 交易对符号
            
        Returns:
            包含持仓量和资金费率的字典
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 获取持仓量
                oi_endpoint = f"{self.base_url}/fapi/v1/openInterest"
                oi_response = requests.get(oi_endpoint, params={'symbol': symbol}, timeout=30)
                oi_response.raise_for_status()
                oi_data = oi_response.json()
                
                # 获取资金费率
                funding_endpoint = f"{self.base_url}/fapi/v1/premiumIndex"
                funding_response = requests.get(funding_endpoint, params={'symbol': symbol}, timeout=30)
                funding_response.raise_for_status()
                funding_data = funding_response.json()
                
                return {
                    'open_interest': float(oi_data.get('openInterest', 0)),
                    'funding_rate': float(funding_data.get('lastFundingRate', 0))
                }
                
            except requests.exceptions.Timeout:
                print(f"获取持仓量/资金费率超时 (尝试 {attempt + 1}/{max_retries}): {symbol}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"获取持仓量/资金费率最终失败: {symbol} - 使用默认值")
                    return {'open_interest': 0, 'funding_rate': 0}
                    
            except Exception as e:
                print(f"获取持仓量和资金费率失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return {'open_interest': 0, 'funding_rate': 0}
        
        return {'open_interest': 0, 'funding_rate': 0}
    
    def format_market_data(self, symbol: str, short_interval: str, long_interval: str, 
                          kline_limit: int = 100) -> str:
        """
        格式化市场数据为文本输出
        
        Args:
            symbol: 交易对符号
            short_interval: 短期K线间隔
            long_interval: 长期K线间隔
            kline_limit: K线数量
            
        Returns:
            格式化的市场数据文本
        """
        # 获取短期K线
        short_klines = self.get_klines(symbol, short_interval, kline_limit)
        if not short_klines:
            return f"无法获取{symbol}的短期数据"
        
        # 获取长期K线
        long_klines = self.get_klines(symbol, long_interval, kline_limit)
        if not long_klines:
            return f"无法获取{symbol}的长期数据"
        
        # 根据开关决定是否跳过最新K线
        effective_short_klines = short_klines[:-1] if self.skip_latest_candle and len(short_klines) > 1 else short_klines
        effective_long_klines = long_klines[:-1] if self.skip_latest_candle and len(long_klines) > 1 else long_klines
        
        # 计算指标
        short_indicators = self.calculate_indicators(effective_short_klines, is_short_term=True)
        long_indicators = self.calculate_indicators(effective_long_klines, is_short_term=False)
        
        # 获取持仓量和资金费率
        oi_funding = self.get_open_interest_and_funding(symbol)
        
        # 获取最新价格
        current_price = effective_short_klines[-1]['close']
        
        # 格式化输出
        output = f"\n{'='*60}\n"
        output += f"ALL {symbol} DATA\n"
        output += f"{'='*60}\n\n"
        
        # 当前主要指标
        output += f"current_price = {current_price:.2f}, "
        output += f"current_ema20 = {short_indicators['ema_20'][-1]:.3f}, "
        output += f"current_macd = {short_indicators['macd'][-1]:.3f}, "
        output += f"current_rsi (7 period) = {short_indicators['rsi_7'][-1]:.3f}\n\n"
        
        # 持仓量和资金费率
        output += f"Open Interest: Latest: {oi_funding['open_interest']:.2f}\n"
        output += f"Funding Rate: {oi_funding['funding_rate']:.2e}\n\n"
        
        # 短期指标（最近10个数据点）
        output += f"Intraday series ({short_interval}, oldest → latest):\n\n"
        
        mid_prices = [k['close'] for k in effective_short_klines[-10:]]
        output += f"Mid prices: {mid_prices}\n\n"
        
        ema_20_recent = [f"{x:.3f}" for x in short_indicators['ema_20'][-10:]]
        output += f"EMA indicators (20‑period): {ema_20_recent}\n\n"
        
        macd_recent = [f"{x:.3f}" for x in short_indicators['macd'][-10:]]
        output += f"MACD indicators: {macd_recent}\n\n"
        
        rsi_7_recent = [f"{x:.3f}" for x in short_indicators['rsi_7'][-10:]]
        output += f"RSI indicators (7‑Period): {rsi_7_recent}\n\n"
        
        rsi_14_recent = [f"{x:.3f}" for x in short_indicators['rsi_14'][-10:]]
        output += f"RSI indicators (14‑Period): {rsi_14_recent}\n\n"
        
        # 长期指标
        output += f"Longer‑term context ({long_interval} timeframe):\n\n"
        
        output += f"20‑Period EMA: {long_indicators['ema_20'][-1]:.3f} "
        output += f"vs. 50‑Period EMA: {long_indicators['ema_50'][-1]:.3f}\n\n"
        
        output += f"3‑Period ATR: {long_indicators['atr_3'][-1]:.2f} "
        output += f"vs. 14‑Period ATR: {long_indicators['atr_14'][-1]:.3f}\n\n"
        
        current_volume = effective_long_klines[-1]['volume']
        avg_volume = np.mean(long_indicators['volumes'][-20:])
        output += f"Current Volume: {current_volume:.3f} vs. Average Volume: {avg_volume:.3f}\n\n"
        
        macd_long_recent = [f"{x:.3f}" for x in long_indicators['macd'][-10:]]
        output += f"MACD indicators: {macd_long_recent}\n\n"
        
        rsi_14_long_recent = [f"{x:.3f}" for x in long_indicators['rsi_14'][-10:]]
        output += f"RSI indicators (14‑Period): {rsi_14_long_recent}\n\n"
        
        return output
    
    def get_account_data(self, initial_capital: Optional[float] = None) -> Dict:
        """
        获取账户数据（需要实现API认证）
        
        Returns:
            账户信息字典
        """
        # 实现：
        # - /fapi/v2/account 获取余额、可用资金等
        # - /fapi/v2/positionRisk 获取逐仓/全仓的持仓信息
        try:
            # 1) 账户信息
            account_endpoint = "/fapi/v2/account"
            account_resp = self._send_signed_request('GET', account_endpoint, {})

            if isinstance(account_resp, dict) and account_resp.get('code'):
                # 交易所返回了错误码
                print(f"获取账户信息出错: {account_resp}")
                return {
                    'total_return_percent': 0.0,
                    'available_cash': 0.0,
                    'account_value': 0.0,
                    'positions': [],
                    'error': account_resp
                }

            total_wallet_balance = float(account_resp.get('totalWalletBalance', 0.0))
            total_unrealized = float(account_resp.get('totalUnrealizedProfit', 0.0))
            total_margin_balance = float(account_resp.get('totalMarginBalance', 0.0))

            # 可用资金（USDT-M常用）：availableBalance 字段
            available_cash = 0.0
            for asset in account_resp.get('assets', []):
                if asset.get('asset') in ('USDT', 'BUSD', 'USDC'):
                    # 以USDT优先
                    if asset.get('asset') == 'USDT':
                        available_cash = float(asset.get('availableBalance', 0.0))
                        break
                    available_cash = float(asset.get('availableBalance', 0.0))

            # 账户价值：使用 totalMarginBalance 更贴近权益
            account_value = total_margin_balance if total_margin_balance > 0 else total_wallet_balance + total_unrealized

            # 2) 持仓信息
            pos_endpoint = "/fapi/v2/positionRisk"
            pos_resp = self._send_signed_request('GET', pos_endpoint, {})

            positions = []
            if isinstance(pos_resp, list):
                for p in pos_resp:
                    try:
                        amt = float(p.get('positionAmt', 0.0))
                        if abs(amt) < 1e-10:
                            continue  # 跳过空仓
                        symbol = p.get('symbol')
                        entry_price = float(p.get('entryPrice', 0.0))
                        mark_price = float(p.get('markPrice', 0.0))
                        liq_price = float(p.get('liquidationPrice', 0.0))
                        unrealized_pnl = float(p.get('unRealizedProfit', 0.0))
                        leverage = int(float(p.get('leverage', 0))) if p.get('leverage') else 0

                        position = {
                            'symbol': symbol,
                            'quantity': abs(amt),
                            'entry_price': entry_price,
                            'current_price': mark_price,
                            'liquidation_price': liq_price,
                            'unrealized_pnl': unrealized_pnl,
                            'leverage': leverage,
                            'direction': 'LONG' if amt > 0 else 'SHORT',
                            'notional_usd': abs(amt * mark_price)
                        }
                        positions.append(position)
                    except Exception:
                        continue
            else:
                # 可能返回错误信息
                print(f"获取持仓信息出错: {pos_resp}")

            # 收益率（无法精确计算初始本金，这里暂置0或由外部维护基线）
            # 收益率计算
            if initial_capital and initial_capital > 0:
                total_return_percent = (account_value - initial_capital) / initial_capital * 100.0
            else:
                total_return_percent = 0.0

            account_data = {
                'total_return_percent': total_return_percent,
                'available_cash': available_cash,
                'account_value': account_value,
                'positions': positions
            }
            return account_data

        except Exception as e:
            print(f"获取账户数据失败: {e}")
            return {
                'total_return_percent': 0.0,
                'available_cash': 0.0,
                'account_value': 0.0,
                'positions': [],
                'error': str(e)
            }
    
    def format_account_data(self, account_data: Dict) -> str:
        """
        格式化账户数据为文本输出
        
        Args:
            account_data: 账户数据字典
            
        Returns:
            格式化的账户数据文本
        """
        output = "\n" + "="*60 + "\n"
        output += "HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE\n"
        output += "="*60 + "\n\n"
        
        output += f"Current Total Return (percent): {account_data.get('total_return_percent', 0):.2f}%\n\n"
        output += f"Available Cash: {account_data.get('available_cash', 0):.1f}\n\n"
        output += f"Current Account Value: {account_data.get('account_value', 0):.1f}\n\n"
        
        positions = account_data.get('positions', [])
        if positions:
            output += "Current live positions & performance:\n"
            for pos in positions:
                output += f"{pos}\n"
        else:
            output += "No current positions\n"
        
        output += "\n"
        return output
    
    def get_all_market_data(self, trading_pairs: List[Dict]) -> str:
        """
        获取所有交易对的市场数据
        
        Args:
            trading_pairs: 交易对配置列表
            
        Returns:
            所有交易对的格式化数据
        """
        all_data = ""
        for pair in trading_pairs:
            symbol = pair['symbol']
            short_interval = pair['short_interval']
            long_interval = pair['long_interval']
            kline_limit = pair.get('kline_limit', 100)
            
            market_data = self.format_market_data(
                symbol, short_interval, long_interval, kline_limit
            )
            all_data += market_data
        
        return all_data


if __name__ == "__main__":
    # 测试代码
    test_config = {
        'api_key': 'test',
        'api_secret': 'test',
        'testnet': True
    }
    
    fetcher = DataFetcher(test_config)
    
    # 测试获取BTC数据
    print("测试获取市场数据...")
    data = fetcher.format_market_data('BTCUSDT', '3m', '4h', 100)
    print(data)
