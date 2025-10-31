"""
数据获取模块
包括交易数据（K线及技术指标）和账户数据的获取
"""
import requests
import talib
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime


class DataFetcher:
    """数据获取类，负责获取市场数据和账户数据"""
    
    def __init__(self, exchange_config: Dict):
        """
        初始化数据获取器
        
        Args:
            exchange_config: 交易所配置信息
        """
        self.api_key = exchange_config.get('api_key')
        self.api_secret = exchange_config.get('api_secret')
        self.testnet = exchange_config.get('testnet', True)
        
        # 根据是否测试网设置基础URL（此处以币安为例）
        if self.testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Dict]:
        """
        获取K线数据
        
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
        
        try:
            response = requests.get(endpoint, params=params, timeout=10)
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
        except Exception as e:
            print(f"获取K线数据失败: {e}")
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
        获取持仓量和资金费率
        
        Args:
            symbol: 交易对符号
            
        Returns:
            包含持仓量和资金费率的字典
        """
        try:
            # 获取持仓量
            oi_endpoint = f"{self.base_url}/fapi/v1/openInterest"
            oi_response = requests.get(oi_endpoint, params={'symbol': symbol}, timeout=10)
            oi_data = oi_response.json()
            
            # 获取资金费率
            funding_endpoint = f"{self.base_url}/fapi/v1/premiumIndex"
            funding_response = requests.get(funding_endpoint, params={'symbol': symbol}, timeout=10)
            funding_data = funding_response.json()
            
            return {
                'open_interest': float(oi_data.get('openInterest', 0)),
                'funding_rate': float(funding_data.get('lastFundingRate', 0))
            }
        except Exception as e:
            print(f"获取持仓量和资金费率失败: {e}")
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
        
        # 计算指标
        short_indicators = self.calculate_indicators(short_klines, is_short_term=True)
        long_indicators = self.calculate_indicators(long_klines, is_short_term=False)
        
        # 获取持仓量和资金费率
        oi_funding = self.get_open_interest_and_funding(symbol)
        
        # 获取最新价格
        current_price = short_klines[-1]['close']
        
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
        
        mid_prices = [k['close'] for k in short_klines[-10:]]
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
        
        current_volume = long_klines[-1]['volume']
        avg_volume = np.mean(long_indicators['volumes'][-20:])
        output += f"Current Volume: {current_volume:.3f} vs. Average Volume: {avg_volume:.3f}\n\n"
        
        macd_long_recent = [f"{x:.3f}" for x in long_indicators['macd'][-10:]]
        output += f"MACD indicators: {macd_long_recent}\n\n"
        
        rsi_14_long_recent = [f"{x:.3f}" for x in long_indicators['rsi_14'][-10:]]
        output += f"RSI indicators (14‑Period): {rsi_14_long_recent}\n\n"
        
        return output
    
    def get_account_data(self) -> Dict:
        """
        获取账户数据（需要实现API认证）
        
        Returns:
            账户信息字典
        """
        # 这里需要实现实际的API调用，包括签名等
        # 以下是示例数据结构
        try:
            # TODO: 实现实际的API调用
            # 这里返回模拟数据作为示例
            account_data = {
                'total_return_percent': 0.0,
                'available_cash': 0.0,
                'account_value': 0.0,
                'positions': []
            }
            return account_data
        except Exception as e:
            print(f"获取账户数据失败: {e}")
            return {}
    
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
