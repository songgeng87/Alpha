"""
交易执行模块
负责实际的交易执行、仓位管理和止损单管理
"""
import requests
import time
import hmac
import hashlib
from typing import Dict, List, Optional
from urllib.parse import urlencode
import os


class TradingExecutor:
    """交易执行器，负责执行交易指令"""
    
    def __init__(self, exchange_config: Dict, confidence_threshold: float = 0.6):
        """
        初始化交易执行器
        
        Args:
            exchange_config: 交易所配置
            confidence_threshold: 信心阈值，低于此值的交易不执行
        """
        # 优先环境变量，其次配置
        api_key_env = exchange_config.get('api_key_env', 'EXCHANGE_API_KEY')
        api_secret_env = exchange_config.get('api_secret_env', 'EXCHANGE_API_SECRET')
        self.api_key = os.getenv(api_key_env) or exchange_config.get('api_key')
        self.api_secret = os.getenv(api_secret_env) or exchange_config.get('api_secret')
        self.testnet = exchange_config.get('testnet', True)
        self.confidence_threshold = confidence_threshold
        
        # 设置API基础URL
        if self.testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
        
        # 存储活跃仓位及其止损单
        self.active_positions = {}  # {symbol: position_info}
        # 交易对规则缓存（精度/步长/最小名义等）
        self._symbol_info_cache: Dict[str, Dict] = {}

    # =========================
    # 交易规则与精度工具方法
    # =========================
    def _get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """获取交易对的精度与过滤规则（带缓存）"""
        if symbol in self._symbol_info_cache:
            return self._symbol_info_cache[symbol]
        try:
            url = f"{self.base_url}/fapi/v1/exchangeInfo"
            r = requests.get(url, params={'symbol': symbol}, timeout=15)
            r.raise_for_status()
            data = r.json()
            symbols = data.get('symbols', [])
            if not symbols:
                return None
            info = symbols[0]
            # 提取常用过滤器
            filters = {f['filterType']: f for f in info.get('filters', [])}
            info['filters_map'] = filters
            self._symbol_info_cache[symbol] = info
            return info
        except Exception as e:
            print(f"获取交易规则失败 {symbol}: {e}")
            return None

    @staticmethod
    def _floor_to_step(value: float, step: float) -> float:
        if step <= 0:
            return value
        # 向下取整到步长
        import math
        return math.floor(value / step) * step

    @staticmethod
    def _round_to_precision(value: float, precision: int) -> float:
        if precision is None:
            return value
        fmt = f"{{:.{precision}f}}"
        return float(fmt.format(value))

    def _normalize_quantity(self, symbol: str, qty: float, price: float, order_type: str = 'LIMIT') -> float:
        """根据交易规则规范化下单数量，满足步长、最小数量、最小名义金额等。

        注意：期货下单存在 LOT_SIZE 与 MARKET_LOT_SIZE 两套过滤器，
        市价单应优先使用 MARKET_LOT_SIZE 的 stepSize/minQty 规则。
        """
        original_qty = qty
        info = self._get_symbol_info(symbol)
        if not info:
            print(f"警告: 无法获取 {symbol} 的交易规则，使用原始数量")
            return qty
        filters = info.get('filters_map', {})

        # 选择合适的数量过滤器
        lot_filter_name = 'LOT_SIZE'
        if (order_type or '').upper() == 'MARKET' and 'MARKET_LOT_SIZE' in filters:
            lot_filter_name = 'MARKET_LOT_SIZE'

        lot = filters.get(lot_filter_name) or {}
        min_qty = float(lot.get('minQty', lot.get('minQty', '0'))) if lot else 0.0
        step_size = float(lot.get('stepSize', lot.get('stepSize', '0'))) if lot else 0.0

        # 处理步长
        if step_size and step_size > 0:
            qty = self._floor_to_step(qty, step_size)

        # 处理最小数量
        if min_qty and qty < min_qty:
            qty = min_qty

        # 最小名义金额（有的为 MIN_NOTIONAL.notional，有的为 NOTIONAL.minNotional）
        min_notional_filter = filters.get('MIN_NOTIONAL') or filters.get('NOTIONAL') or {}
        min_notional_value = (
            min_notional_filter.get('notional')
            if 'notional' in min_notional_filter
            else min_notional_filter.get('minNotional', '0')
        )
        try:
            min_notional = float(min_notional_value or 0)
        except Exception:
            min_notional = 0.0
        notional = qty * price if price else 0.0
        if min_notional and notional < min_notional and price:
            # 向上调整到满足最小名义金额，再按步长取整
            target_qty = min_notional / price
            if step_size and step_size > 0:
                import math
                target_qty = math.ceil(target_qty / step_size) * step_size
            qty = max(qty, target_qty)

        # 限制数量精度（quantityPrecision）
        q_prec = info.get('quantityPrecision')
        if isinstance(q_prec, int):
            qty = self._round_to_precision(qty, q_prec)

        # 打印规范化信息
        if abs(original_qty - qty) > 0.0001:
            print(f"数量规范化: {symbol} {original_qty:.8f} → {qty} (过滤器={lot_filter_name}, 步长={step_size}, 精度={q_prec})")
        
        return qty

    def _normalize_price(self, symbol: str, price: float) -> float:
        """根据交易规则规范化价格"""
        original_price = price
        info = self._get_symbol_info(symbol)
        if not info:
            return price
        filters = info.get('filters_map', {})
        price_filter = filters.get('PRICE_FILTER') or {}
        tick_size = float(price_filter.get('tickSize', '0')) if price_filter else 0.0
        if tick_size and tick_size > 0:
            price = self._floor_to_step(price, tick_size)
        p_prec = info.get('pricePrecision')
        if isinstance(p_prec, int):
            price = self._round_to_precision(price, p_prec)
        
        # 打印规范化信息
        if abs(original_price - price) > 0.0001:
            print(f"价格规范化: {symbol} {original_price:.8f} → {price} (步长={tick_size}, 精度={p_prec})")
        
        return price

    @staticmethod
    def _is_error_response(resp: Dict) -> bool:
        return isinstance(resp, dict) and ('code' in resp) and (str(resp.get('code')) != '0')
    
    def _generate_signature(self, params: Dict) -> str:
        """
        生成API签名
        
        Args:
            params: 请求参数
            
        Returns:
            签名字符串
        """
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
                print(f"交易请求超时 [{method} {endpoint}] (尝试 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return {"code": -1, "msg": "REQUEST_TIMEOUT", "error": "请求超时"}
                    
            except requests.exceptions.RequestException as e:
                print(f"交易请求网络错误 [{method} {endpoint}] (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    try:
                        return r.json()
                    except Exception:
                        return {"code": -1, "msg": "NETWORK_ERROR", "error": str(e)}
                        
            except Exception as e:
                print(f"交易请求失败 [{method} {endpoint}]: {e}")
                return {"code": -1, "msg": "UNKNOWN_ERROR", "error": str(e)}
        
        return {"code": -1, "msg": "MAX_RETRIES_EXCEEDED"}
    
    def get_position_info(self, symbol: str) -> Optional[Dict]:
        """
        获取指定交易对的仓位信息
        
        Args:
            symbol: 交易对符号
            
        Returns:
            仓位信息
        """
        endpoint = "/fapi/v2/positionRisk"
        params = {}
        
        result = self._send_signed_request('GET', endpoint, params)
        
        if result:
            for position in result:
                if position['symbol'] == symbol:
                    return position
        
        return None
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        设置杠杆倍数
        
        Args:
            symbol: 交易对符号
            leverage: 杠杆倍数
            
        Returns:
            是否成功
        """
        # 先校验交易对是否有效
        if not self._get_symbol_info(symbol):
            print(f"无效或未知交易对: {symbol}，无法设置杠杆")
            return False
        endpoint = "/fapi/v1/leverage"
        params = {
            'symbol': symbol,
            'leverage': leverage
        }
        
        result = self._send_signed_request('POST', endpoint, params)
        if result and not self._is_error_response(result):
            print(f"设置 {symbol} 杠杆为 {leverage}x 成功")
            return True
        else:
            print(f"设置 {symbol} 杠杆失败: {result}")
            return False
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """
        下市价单
        
        Args:
            symbol: 交易对符号
            side: 买卖方向（BUY/SELL）
            quantity: 数量
            
        Returns:
            订单信息
        """
        # 先校验交易对是否有效
        info = self._get_symbol_info(symbol)
        if not info:
            print(f"无效或未知交易对: {symbol}，取消下单")
            return None

        # 先按规则规范化数量
        # 获取最新价格用于名义金额判断：这里简化为通过标的最新价接口获取一次
        try:
            r = requests.get(f"{self.base_url}/fapi/v1/ticker/price", params={'symbol': symbol}, timeout=10)
            r.raise_for_status()
            price = float(r.json().get('price', '0'))
        except Exception:
            price = 0.0

        norm_qty = self._normalize_quantity(symbol, float(quantity), price, order_type='MARKET')
        if norm_qty <= 0:
            print(f"数量规范化后无效，取消下单: 原数量={quantity}, 规范化后={norm_qty}")
            return None

        endpoint = "/fapi/v1/order"
        # 注意：不要在这里添加timestamp和signature，这些会在_send_signed_request中添加
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': norm_qty
        }

        result = self._send_signed_request('POST', endpoint, params)
        
        if result and not self._is_error_response(result):
            print(f"市价单执行成功: {symbol} {side} {norm_qty}")
            return result
        else:
            print(f"市价单执行失败: {symbol} {side} {norm_qty}，返回: {result}")
            return None
    
    def place_stop_loss_order(self, symbol: str, side: str, quantity: float, 
                             stop_price: float) -> Optional[Dict]:
        """
        下止损单
        
        Args:
            symbol: 交易对符号
            side: 买卖方向（BUY/SELL）
            quantity: 数量
            stop_price: 止损价格
            
        Returns:
            订单信息
        """
        # 规范化止损价格
        norm_price = self._normalize_price(symbol, float(stop_price))
        endpoint = "/fapi/v1/order"
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'STOP_MARKET',
            'stopPrice': norm_price,
            'closePosition': 'true'  # 直接平仓
        }
        
        result = self._send_signed_request('POST', endpoint, params)
        
        if result and not self._is_error_response(result):
            print(f"止损单设置成功: {symbol} {side} @ {norm_price}")
            return result
        else:
            print(f"止损单设置失败: {symbol} {side} @ {norm_price}，返回: {result}")
            return None
    
    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """
        取消订单
        
        Args:
            symbol: 交易对符号
            order_id: 订单ID
            
        Returns:
            是否成功
        """
        endpoint = "/fapi/v1/order"
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        
        result = self._send_signed_request('DELETE', endpoint, params)
        if result and not self._is_error_response(result):
            print(f"订单 {order_id} 取消成功")
            return True
        else:
            print(f"订单 {order_id} 取消失败: {result}")
            return False
    
    def cancel_all_stop_loss_orders(self, symbol: str) -> bool:
        """
        取消指定交易对的所有止损单
        
        Args:
            symbol: 交易对符号
            
        Returns:
            是否成功
        """
        # 获取所有未成交订单
        endpoint = "/fapi/v1/openOrders"
        params = {'symbol': symbol}
        
        orders = self._send_signed_request('GET', endpoint, params)
        
        if not orders or self._is_error_response(orders):
            return True
        
        # 取消所有止损单
        success = True
        for order in orders:
            if order.get('type') in ['STOP_MARKET', 'STOP']:
                if not self.cancel_order(symbol, order['orderId']):
                    success = False
        
        return success
    
    def execute_open_position(self, trade: Dict, available_cash: float) -> bool:
        """
        执行开仓操作
        
        Args:
            trade: 交易指令
            available_cash: 可用资金
            
        Returns:
            是否成功
        """
        symbol = trade['symbol']
        direction = trade['direction']  # LONG or SHORT
        leverage = int(trade['leverage'])
        position_size_percent = trade['position_size_percent']
        stop_loss = trade['stop_loss']
        
        # 设置杠杆
        if not self.set_leverage(symbol, leverage):
            return False
        
        # 计算仓位大小
        position_value = available_cash * position_size_percent * leverage
        
        # 获取当前价格来计算数量
        # 这里简化处理，实际应该获取最新价格
        entry_price = trade.get('entry_price_target', 0)
        if entry_price <= 0:
            print(f"无效的入场价格: {entry_price}")
            return False
        
        quantity = position_value / entry_price
        
        # 下市价单开仓
        side = 'BUY' if direction == 'LONG' else 'SELL'
        order = self.place_market_order(symbol, side, quantity)
        if not order:
            # 确保没有残留的止损条件单（防御性清理）
            self.cancel_all_stop_loss_orders(symbol)
            return False
        
        # 设置止损单
        stop_side = 'SELL' if direction == 'LONG' else 'BUY'
        stop_order = self.place_stop_loss_order(symbol, stop_side, quantity, stop_loss)
        
        # 记录仓位信息
        self.active_positions[symbol] = {
            'direction': direction,
            'quantity': quantity,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'leverage': leverage,
            'stop_order_id': stop_order['orderId'] if stop_order else None
        }
        
        return True
    
    def execute_close_position(self, trade: Dict) -> bool:
        """
        执行平仓操作
        
        Args:
            trade: 交易指令
            
        Returns:
            是否成功
        """
        symbol = trade['symbol']
        
        # 检查是否有仓位
        if symbol not in self.active_positions:
            print(f"没有 {symbol} 的活跃仓位")
            return False
        
        position = self.active_positions[symbol]
        
        # 取消止损单
        if position.get('stop_order_id'):
            self.cancel_order(symbol, position['stop_order_id'])
        
        # 平仓
        direction = position['direction']
        quantity = position['quantity']
        side = 'SELL' if direction == 'LONG' else 'BUY'
        
        order = self.place_market_order(symbol, side, quantity)
        
        if order:
            # 从活跃仓位中移除
            del self.active_positions[symbol]
            return True
        
        return False
    
    def execute_trades(self, trades: List[Dict], available_cash: float) -> Dict:
        """
        执行一组交易指令
        
        Args:
            trades: 交易指令列表
            available_cash: 可用资金
            
        Returns:
            执行结果统计
        """
        results = {
            'total': len(trades),
            'executed': 0,
            'skipped_low_confidence': 0,
            'failed': 0,
            'details': []
        }
        
        for trade in trades:
            symbol = trade.get('symbol', 'UNKNOWN')
            action = trade.get('action', 'UNKNOWN')
            confidence = trade.get('confidence', 0)
            
            print(f"\n处理交易: {symbol} - {action} (信心度: {confidence:.2f})")
            
            # 检查信心度
            if confidence < self.confidence_threshold:
                print(f"信心度 {confidence:.2f} 低于阈值 {self.confidence_threshold}，跳过")
                results['skipped_low_confidence'] += 1
                results['details'].append({
                    'symbol': symbol,
                    'action': action,
                    'status': 'skipped_low_confidence'
                })
                continue
            
            # 检查是否为亏损状态下的平仓（根据需求，亏损时不平仓）
            if action == 'CLOSE' and symbol in self.active_positions:
                position = self.active_positions[symbol]
                current_price = trade.get('entry_price_target', position['entry_price'])
                entry_price = position['entry_price']
                direction = position['direction']
                
                # 判断是否亏损
                is_loss = False
                if direction == 'LONG' and current_price < entry_price:
                    is_loss = True
                elif direction == 'SHORT' and current_price > entry_price:
                    is_loss = True
                
                if is_loss:
                    print(f"当前持仓亏损，不执行平仓操作")
                    results['skipped_low_confidence'] += 1
                    results['details'].append({
                        'symbol': symbol,
                        'action': action,
                        'status': 'skipped_loss_position'
                    })
                    continue
            
            # 执行交易
            success = False
            
            if action == 'OPEN':
                success = self.execute_open_position(trade, available_cash)
            elif action == 'CLOSE':
                success = self.execute_close_position(trade)
            elif action == 'HOLD':
                print(f"保持 {symbol} 仓位")
                success = True
            elif action in ['BP', 'SP']:
                # 突破交易，类似开仓
                print(f"执行突破交易: {action}")
                success = self.execute_open_position(trade, available_cash)
            else:
                print(f"未知的交易动作: {action}")
            
            if success:
                results['executed'] += 1
                results['details'].append({
                    'symbol': symbol,
                    'action': action,
                    'status': 'success'
                })
            else:
                results['failed'] += 1
                results['details'].append({
                    'symbol': symbol,
                    'action': action,
                    'status': 'failed'
                })
        
        return results
    
    def get_active_positions_summary(self) -> str:
        """
        获取当前活跃仓位摘要
        
        Returns:
            仓位摘要文本
        """
        if not self.active_positions:
            return "当前无活跃仓位"
        
        summary = "当前活跃仓位:\n"
        for symbol, position in self.active_positions.items():
            summary += f"  {symbol}: {position['direction']} "
            summary += f"{position['quantity']:.4f} @ {position['entry_price']:.2f} "
            summary += f"(杠杆: {position['leverage']}x, 止损: {position['stop_loss']:.2f})\n"
        
        return summary


if __name__ == "__main__":
    # 测试代码
    test_config = {
        'api_key': 'test',
        'api_secret': 'test',
        'testnet': True
    }
    
    executor = TradingExecutor(test_config, confidence_threshold=0.6)
    print("交易执行器已初始化")
    print(f"信心阈值: {executor.confidence_threshold}")
