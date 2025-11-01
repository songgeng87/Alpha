# AI交易建议API服务

基于Flask的Web API服务，提供AI驱动的加密货币交易建议查询功能。

## 功能特性

- 🤖 **AI分析**: 调用DeepSeek等大模型分析市场数据
- 📊 **技术指标**: 自动计算EMA、MACD、RSI、ATR等技术指标
- 🎯 **多币种支持**: 可同时查询多个交易对的建议
- 🌐 **Web界面**: 提供友好的前端页面，无需编写代码
- 🔌 **RESTful API**: 标准HTTP接口，方便集成

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

确保已安装：
- Flask >= 3.0.0
- Flask-CORS >= 4.0.0
- 其他项目依赖（requests, numpy, TA-Lib, python-dotenv）

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# DeepSeek API密钥（必需）
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Binance API密钥（用于获取市场数据）
EXCHANGE_API_KEY=your_binance_api_key
EXCHANGE_API_SECRET=your_binance_api_secret

# API服务配置（可选）
API_HOST=0.0.0.0
API_PORT=5000
API_DEBUG=False
```

### 3. 启动服务

```bash
python3 server.py
```

服务启动后将显示：

```
============================================================
AI交易建议API服务
============================================================
服务地址: http://0.0.0.0:5000
API文档: http://0.0.0.0:5000/api/health
前端页面: http://0.0.0.0:5000/
============================================================
```

### 4. 访问Web界面

打开浏览器访问 http://localhost:5000

## API文档

### 1. 获取AI交易建议

**端点**: `POST /api/get_advice`

**请求体**:
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT"],
  "short_interval": "3m",
  "long_interval": "4h",
  "kline_limit": 1000
}
```

**参数说明**:
- `symbols` (必需): 交易对数组，例如 ["BTCUSDT", "ETHUSDT"]
- `short_interval` (必需): 短期时间周期
  - 可选值: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
- `long_interval` (必需): 长期时间周期
  - 可选值: 同上
- `kline_limit` (可选): K线数量，默认1000

**响应示例**:
```json
{
  "success": true,
  "symbols": ["BTCUSDT", "ETHUSDT"],
  "short_interval": "3m",
  "long_interval": "4h",
  "ai_count": 1,
  "decisions": [
    {
      "ai_name": "DeepSeek",
      "analysis": "市场整体呈现震荡偏弱格局...",
      "trades": [
        {
          "action": "HOLD",
          "symbol": "BTCUSDT",
          "direction": "LONG",
          "leverage": 0,
          "position_size_percent": 0.0,
          "entry_price_target": 0,
          "stop_loss": 0,
          "confidence": 0.6,
          "reason": "当前持仓浮亏，根据规则不在亏损时平仓..."
        }
      ]
    }
  ]
}
```

**错误响应**:
```json
{
  "success": false,
  "error": "错误描述"
}
```

### 2. 获取可用交易对列表

**端点**: `GET /api/available_symbols`

**响应示例**:
```json
{
  "success": true,
  "symbols": [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "ZENUSDT",
    "VIRTUALUSDT"
  ]
}
```

### 3. 健康检查

**端点**: `GET /api/health`

**响应示例**:
```json
{
  "status": "healthy",
  "service": "AI Trading Advice API"
}
```

## 交易动作说明

AI返回的交易建议中，`action` 字段包含以下值：

- **OPEN**: 开新仓位
- **CLOSE**: 平仓现有仓位
- **HOLD**: 持有现有仓位（观望）
- **BP**: 突破买入（Breakout Purchase）
- **SP**: 突破卖出（Breakout Sale）

## 使用场景

### 场景1: 快速查询单个币种建议

```bash
curl -X POST http://localhost:5000/api/get_advice \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTCUSDT"],
    "short_interval": "5m",
    "long_interval": "1h"
  }'
```

### 场景2: 批量查询多个币种

```bash
curl -X POST http://localhost:5000/api/get_advice \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "short_interval": "3m",
    "long_interval": "4h",
    "kline_limit": 500
  }'
```

### 场景3: 使用Web界面

1. 访问 http://localhost:5000
2. 勾选想要查询的交易对
3. 选择短期和长期时间周期
4. 点击"获取AI建议"按钮
5. 查看AI分析结果和具体交易建议

## 技术架构

```
server.py (Flask API)
    ↓
data_fetcher.py (获取K线数据和技术指标)
    ↓
ai_decision.py (调用AI模型分析)
    ↓
返回JSON格式的交易建议
```

## 前端页面特性

- 📱 响应式设计，支持移动端访问
- 🎨 现代化UI，渐变色背景和卡片式布局
- ⚡ 实时反馈，加载动画和错误提示
- 📊 可视化展示，信心度进度条
- 🔄 动态加载可用交易对列表

## 注意事项

1. **API密钥安全**: 
   - 不要将API密钥提交到版本控制
   - 使用环境变量存储敏感信息
   - 生产环境建议使用只读API密钥

2. **请求频率**:
   - Binance API有请求频率限制
   - AI API可能有调用配额限制
   - 建议合理控制查询频率

3. **数据准确性**:
   - 市场数据实时变化，建议定期刷新
   - AI建议仅供参考，不构成投资建议
   - 请结合自身判断做出交易决策

4. **性能优化**:
   - 默认查询1000根K线，可根据需要调整
   - 多个交易对会增加响应时间
   - 考虑添加缓存机制优化性能

## 与自动交易系统的区别

| 特性 | API服务 (server.py) | 自动交易系统 (main.py) |
|------|---------------------|----------------------|
| 用途 | 查询建议 | 自动执行交易 |
| 持仓状态 | 假设无持仓 | 跟踪真实持仓 |
| 交易执行 | 不执行 | 实际下单 |
| 运行方式 | Web服务 | 后台守护进程 |
| 适用场景 | 辅助决策 | 无人值守交易 |

## 故障排查

### 问题1: 无法启动服务

**错误**: `ImportError: No module named 'flask'`

**解决**: 
```bash
pip install Flask Flask-CORS
```

### 问题2: API返回错误

**错误**: `"error": "无法获取市场数据"`

**解决**:
1. 检查 Binance API 密钥是否正确
2. 确认网络连接正常
3. 查看控制台详细错误日志

### 问题3: AI未返回建议

**错误**: `"error": "所有AI模型均未返回有效决策"`

**解决**:
1. 检查 DeepSeek API 密钥是否配置
2. 确认 API 配额是否充足
3. 查看 `ai_history/` 目录下的交互记录

## 扩展开发

### 添加新的AI模型

编辑 `config.json`:

```json
{
  "ai_models": [
    {
      "name": "DeepSeek",
      "api_url": "https://api.deepseek.com/v1/chat/completions",
      "api_key_env": "DEEPSEEK_API_KEY",
      "model": "deepseek-chat"
    },
    {
      "name": "GPT-4",
      "api_url": "https://api.openai.com/v1/chat/completions",
      "api_key_env": "OPENAI_API_KEY",
      "model": "gpt-4"
    }
  ]
}
```

### 自定义响应格式

修改 `server.py` 中的 `get_ai_advice` 函数，调整返回的数据结构。

### 添加认证机制

在 Flask 中添加 API Token 验证：

```python
from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != os.getenv('API_SECRET_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/get_advice', methods=['POST'])
@require_api_key
def api_get_advice():
    # ...
```

## 许可证

本项目与主交易系统共享相同的许可证。

## 技术支持

遇到问题或有建议？
- 查看主项目 README
- 检查 `ai_history/` 目录下的API调用记录
- 查看服务器控制台日志
