# AI 交易系统
我将告诉DeepSeek目前的市场情况以及我的持仓情况，然后等待他的答复，最后根据他的答复在币安合约市场进行交易。
目前我准备交易的是BTC、ETH、SOL、DOGE、BNB这五个币对应的USDT永续合约，但是未来我可能增加或者删除币种。
我的启动资金将会是10000 USDT。

## Prompt信息
prompt信息由三部分组成：
总体信息、市场信息和持仓信息
### 总体信息如下组织
It has been 6934 minutes since you started trading. The current time is 2025-10-27 08:42:49.800631 and you've been invoked 2742 times. Below, we are providing you with a variety of state data, price data, and predictive signals so you can discover alpha. Below that is your current account information, value, performance, positions, etc.

ALL OF THE PRICE OR SIGNAL DATA BELOW IS ORDERED: OLDEST → NEWEST

Timeframes note: Unless stated otherwise in a section title, intraday series are provided at 3‑minute intervals. If a coin uses a different interval, it is explicitly stated in that coin’s section.

### 市场信息如下组织：

ALL BTC DATA
current_price = 115328.5, current_ema20 = 115548.561, current_macd = -123.451, current_rsi (7 period) = 30.911

In addition, here is the latest BTC open interest and funding rate for perps (the instrument you are trading):

Open Interest: Latest: 29783.27 Average: 29828.8

Funding Rate: 1.25e-05

Intraday series (by minute, oldest → latest):

Mid prices: [115543.0, 115519.0, 115497.5, 115564.5, 115580.5, 115516.5, 115339.5, 115257.5, 115413.5, 115328.5]

EMA indicators (20‑period): [115707.514, 115686.036, 115669.557, 115662.837, 115651.9, 115636.005, 115608.766, 115586.027, 115571.357, 115548.561]

MACD indicators: [-104.3, -110.611, -111.823, -104.637, -101.883, -103.59, -114.516, -120.176, -118.295, -123.451]

RSI indicators (7‑Period): [31.668, 28.577, 34.505, 48.374, 42.192, 35.631, 25.656, 29.087, 39.231, 30.911]

RSI indicators (14‑Period): [39.045, 37.326, 39.602, 45.515, 42.837, 39.727, 34.027, 35.503, 39.987, 35.679]

Longer‑term context (4‑hour timeframe):

20‑Period EMA: 112440.121 vs. 50‑Period EMA: 111235.431

3‑Period ATR: 575.24 vs. 14‑Period ATR: 658.474

Current Volume: 12.628 vs. Average Volume: 4737.211

MACD indicators: [641.669, 650.401, 620.872, 633.819, 769.48, 889.972, 961.709, 1082.258, 1206.811, 1325.662]

RSI indicators (14‑Period): [60.613, 60.199, 56.894, 60.384, 68.763, 69.947, 68.424, 72.327, 74.258, 75.761]

ALL ETH DATA
current_price = 4176.55, current_ema20 = 4194.891, current_macd = -12.535, current_rsi (7 period) = 29.694

In addition, here is the latest ETH open interest and funding rate for perps:

Open Interest: Latest: 504375.72 Average: 505811.88

Funding Rate: 1.25e-05

Intraday series (3‑minute intervals, oldest → latest):

Mid prices: [4199.95, 4192.25, 4190.9, 4196.45, 4195.65, 4190.95, 4181.75, 4167.05, 4174.25, 4176.55]

EMA indicators (20‑period): [4211.31, 4209.28, 4207.616, 4206.805, 4205.499, 4203.899, 4201.947, 4199.019, 4196.827, 4194.891]

MACD indicators: [-10.254, -10.78, -10.925, -10.333, -10.229, -10.383, -10.807, -11.99, -12.397, -12.535]

RSI indicators (7‑Period): [34.624, 23.929, 28.698, 45.007, 36.911, 31.988, 26.939, 18.919, 28.667, 29.694]

RSI indicators (14‑Period): [33.197, 27.895, 30.125, 38.441, 34.777, 32.343, 29.651, 24.579, 29.676, 30.205]

Longer‑term context (4‑hour timeframe):

20‑Period EMA: 4019.387 vs. 50‑Period EMA: 3973.825

3‑Period ATR: 35.348 vs. 14‑Period ATR: 38.119

Current Volume: 438.368 vs. Average Volume: 100521.565

MACD indicators: [10.572, 12.047, 11.382, 12.702, 21.696, 29.891, 35.278, 46.602, 58.685, 67.108]

RSI indicators (14‑Period): [56.494, 55.395, 52.105, 55.442, 65.949, 67.377, 65.898, 72.841, 75.516, 74.722]

### 持仓信息如下组织
HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE
Current Total Return (percent): 122.93%

Available Cash: 13654.1

Current Account Value: 22293.0

Current live positions & performance: {'symbol': 'ETH', 'quantity': 5.74, 'entry_price': 4189.12, 'current_price': 4176.75, 'liquidation_price': 3848.61, 'unrealized_pnl': -71.0, 'leverage': 10, 'exit_plan': {'profit_target': 4568.31, 'stop_loss': 4065.43, 'invalidation_condition': 'If the price closes below 4000 on a 3-minute candle'}, 'confidence': 0.65, 'risk_usd': 722.7846, 'sl_oid': 213487996496, 'tp_oid': 213487981580, 'wait_for_fill': False, 'entry_oid': 213487963080, 'notional_usd': 23974.55} {'symbol': 'SOL', 'quantity': 33.88, 'entry_price': 198.82, 'current_price': 200.455, 'liquidation_price': 183.58, 'unrealized_pnl': 55.39, 'leverage': 10, 'exit_plan': {'profit_target': 215.0, 'stop_loss': 192.86, 'invalidation_condition': 'If the price closes below 190 on a 3-minute candle'}, 'confidence': 0.65, 'risk_usd': 202.07655, 'sl_oid': 213307544465, 'tp_oid': 213307526843, 'wait_for_fill': False, 'entry_oid': 213307507703, 'notional_usd': 6791.42} {'symbol': 'XRP', 'quantity': 3609.0, 'entry_price': 2.44, 'current_price': 2.62875, 'liquidation_price': 2.26, 'unrealized_pnl': 663.88, 'leverage': 10, 'exit_plan': {'profit_target': 2.815, 'stop_loss': 2.325, 'invalidation_condition': 'If the price closes below 2.30 on a 3-minute candle'}, 'confidence': 0.65, 'risk_usd': 442.032, 'sl_oid': -1, 'tp_oid': -1, 'wait_for_fill': False, 'entry_oid': 211217736949, 'notional_usd': 9487.16} {'symbol': 'BTC', 'quantity': 0.12, 'entry_price': 107343.0, 'current_price': 115314.5, 'liquidation_price': 98095.25, 'unrealized_pnl': 956.58, 'leverage': 10, 'exit_plan': {'invalidation_condition': 'If the price closes below 105000 on a 3-minute candle', 'profit_target': 118136.15, 'stop_loss': 102026.675}, 'confidence': 0.75, 'risk_usd': 619.2345, 'sl_oid': 206132736980, 'tp_oid': 206132723593, 'wait_for_fill': False, 'entry_oid': 206132712257, 'notional_usd': 13837.74} {'symbol': 'DOGE', 'quantity': 27858.0, 'entry_price': 0.18, 'current_price': 0.205145, 'liquidation_price': 0.18, 'unrealized_pnl': 573.07, 'leverage': 10, 'exit_plan': {'invalidation_condition': 'If the price closes below 0.180 on a 3-minute candle', 'profit_target': 0.212275, 'stop_loss': 0.175355}, 'confidence': 0.65, 'risk_usd': 257.13, 'sl_oid': -1, 'tp_oid': -1, 'wait_for_fill': False, 'entry_oid': 204672918246, 'notional_usd': 5714.93} {'symbol': 'BNB', 'quantity': 5.64, 'entry_price': 1140.6, 'current_price': 1157.25, 'liquidation_price': 1081.06, 'unrealized_pnl': 93.91, 'leverage': 10, 'exit_plan': {'profit_target': 1254.29, 'stop_loss': 1083.23, 'invalidation_condition': 'If the price closes below 1080 on a 3-minute candle'}, 'confidence': 0.65, 'risk_usd': 321.61725, 'sl_oid': 213425666937, 'tp_oid': 213425655129, 'wait_for_fill': False, 'entry_oid': 213425641486, 'notional_usd': 6526.89}

Sharpe Ratio: 0.549