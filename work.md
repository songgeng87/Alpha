我要创建一个基于AI决策的数字货币合约市场自动交易系统。
这个系统由3个独立子部分+1个main文件组成：
1.数据获取部分
数据获取部分包括交易数据和账户数据

交易数据将最终获取短期指标和长期指标，这个根据函数传入，比如短期是3分钟，长期是4小时，每次分别获取100根K线。
然后采用ta-lib进行专业处理。
最后组成一下类似指标，注意Intraday series的指标采用短期K线计算，
Longer‑term context的指标采用长期K线计算。
{ ALL BTC DATA
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
}

数据获取部分,最后按以上文本格式输出。支持一次输出多组交易对的数据。

账户数据按一下格式获取并组织成文本
{HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE
Current Total Return (percent): 122.93%

Available Cash: 13654.1

Current Account Value: 22293.0

Current live positions & performance: {'symbol': 'ETH', 'quantity': 5.74, 'entry_price': 4189.12, 'current_price': 4176.75, 'liquidation_price': 3848.61, 'unrealized_pnl': -71.0, 'leverage': 10, 'exit_plan': {'profit_target': 4568.31, 'stop_loss': 4065.43, 'invalidation_condition': 'If the price closes below 4000 on a 3-minute candle'}, 'confidence': 0.65, 'risk_usd': 722.7846, 'sl_oid': 213487996496, 'tp_oid': 213487981580, 'wait_for_fill': False, 'entry_oid': 213487963080, 'notional_usd': 23974.55}

}
2.决策部分
决策部分支持多组AI（都以openai的api格式进行处理），通过询问不同的AI（也可以只询问一个），获得交易建议，这些建议都以统一格式输出。然后将他们交易建议进行总结比较，操作、方向完全一致的交易才形成最终的交易建议。具体的仓位、杠杆等以第一个AI的建议为准。

每个AI的输入都是一致的。
AI输入的user部分，每次都从一个文件里面读取。内容包括告诉AI，他是一个专业的数字货币合约交易员，擅长趋势交易。通过分析短期指标和长期指标能给出非常专业的交易建议，并严格按照以下JSON格式返回

"回复必须严格按照以下JSON格式返回，不要添加任何其他文字：
{
    "analysis": "对当前市场情况的分析",
    "trades": [
        {
            "action": "OPEN|CLOSE|HOLD|BP|SP",
            "symbol": "BTCUSDT",
            "direction": "LONG|SHORT",
            "leverage": 5-10,
            "position_size_percent": 0.05-0.10,
            "entry_price_target": 价格,
            "stop_loss": 止损价格,
            "confidence": 0.1-1.0,
            "reason": "操作理由"
        }
    ]
}

操作说明:
- OPEN: 开新仓位
- CLOSE: 平仓现有仓位
- HOLD: 持有现有仓位
- BP: 突破买入
- SP: 突破卖出
- direction: LONG(做多) 或 SHORT(做空)
- leverage: 杠杆倍数(5-10倍)
- position_size_percent: 仓位大小占可用资金的百分比(0.05-0.10)
- confidence: 信心等级(0.1-1.0)

请确保回复是有效的JSON格式。"
只有当长期信号和短期信号一致时，才给出除HOLD以外的建议。
在建仓、加仓时，同时给出止损条件,不需要给止盈条件。
在后期对该仓位的建议中，不会在持仓亏损的情况下给出CLOSE或者减仓指令。

prompt部分，由前缀、市场数据、账户数据和后缀四部分组成，后缀内容每次从文件里面读取。前缀、市场数据、账户数据内容都由函数传入

3.交易部分通过输入的一组交易指令完成实际交易，在CLOSE的情况下，要撤销对应的止损单。同时提供信心判断参数，只有信心指数大于这个指时，才执行交易。

4.main文件，配置文件里面读取想要交易的交易对组，想要询问的AI组，同时对询问的次数等给出记录，形成prompt的前缀部分如下：
It has been 6934 minutes since you started trading. The current time is 2025-10-27 08:42:49.800631 and you've been invoked 2742 times. Below, we are providing you with a variety of state data, price data, and predictive signals so you can discover alpha. Below that is your current account information, value, performance, positions, etc.

ALL OF THE PRICE OR SIGNAL DATA BELOW IS ORDERED: OLDEST → NEWEST

Timeframes note: Unless stated otherwise in a section title, intraday series are provided at 3‑minute intervals. If a coin uses a different interval, it is explicitly stated in that 