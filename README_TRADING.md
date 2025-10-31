# AI驱动的数字货币自动交易系统

这是一个基于AI决策的数字货币合约自动交易系统，通过多个AI模型分析市场数据，形成一致的交易建议并自动执行。

## 系统架构

系统由4个主要模块组成：

1. **数据获取模块** (`data_fetcher.py`)
   - 获取K线数据（支持短期和长期时间框架）
   - 使用TA-Lib计算技术指标（EMA、MACD、RSI、ATR等）
   - 获取持仓量和资金费率
   - 获取账户信息和仓位数据
   - 格式化输出市场数据和账户数据

2. **AI决策模块** (`ai_decision.py`)
   - 支持多个AI模型（OpenAI API格式）
   - 从文件加载提示词模板
   - 整合市场数据和账户数据形成完整提示词
   - 解析AI返回的JSON交易建议
   - 汇总多个AI的建议，只执行完全一致的交易

3. **交易执行模块** (`trading_executor.py`)
   - 执行开仓、平仓操作
   - 自动设置杠杆和止损单
   - 支持信心度阈值过滤
   - 在CLOSE时自动撤销止损单
   - 防止在亏损状态下平仓
   - 管理活跃仓位

4. **主程序** (`main.py`)
   - 协调各模块的工作流程
   - 管理系统状态（运行时间、调用次数）
   - 生成带有上下文的提示词前缀
   - 支持单次运行和持续运行模式

## 目录结构

```
Alpha/
├── main.py                    # 主程序
├── data_fetcher.py           # 数据获取模块
├── ai_decision.py            # AI决策模块
├── trading_executor.py       # 交易执行模块
├── config.json               # 配置文件
├── requirements.txt          # Python依赖
├── prompts/                  # 提示词目录
│   ├── user_instruction.txt  # AI角色和格式说明
│   └── suffix.txt           # 提示词后缀
├── invocation_count.txt      # 调用次数记录
└── README.md                # 本文件
```

## 安装

### 1. 安装Python依赖

首先需要安装TA-Lib库。在macOS上：

```bash
# 安装TA-Lib C库
brew install ta-lib

# 安装Python包
pip install -r requirements.txt
```

在Linux上：

```bash
# 下载并安装TA-Lib
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install

# 安装Python包
pip install -r requirements.txt
```

### 2. 配置系统

编辑 `config.json` 文件：

```json
{
    "trading_pairs": [
        {
            "symbol": "BTCUSDT",
            "short_interval": "3m",
            "long_interval": "4h",
            "kline_limit": 100
        }
    ],
    "ai_models": [
        {
            "name": "GPT-4",
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_key": "YOUR_API_KEY_HERE",
            "model": "gpt-4"
        }
    ],
    "exchange": {
        "api_key": "YOUR_EXCHANGE_API_KEY",
        "api_secret": "YOUR_EXCHANGE_API_SECRET",
        "testnet": true
    },
    "trading_settings": {
        "confidence_threshold": 0.6,
        "max_positions": 3,
        "leverage_range": [5, 10],
        "position_size_range": [0.05, 0.10]
    }
}
```

**重要配置项说明：**

- `trading_pairs`: 要交易的币种列表
  - `symbol`: 交易对符号
  - `short_interval`: 短期K线间隔（如"3m"）
  - `long_interval`: 长期K线间隔（如"4h"）
  - `kline_limit`: 获取的K线数量

- `ai_models`: AI模型配置
  - `name`: 模型名称
  - `api_url`: API端点
  - `api_key`: API密钥
  - `model`: 模型版本

- `exchange`: 交易所配置
  - `api_key`: 交易所API密钥
  - `api_secret`: 交易所API密钥
  - `testnet`: 是否使用测试网

- `trading_settings`: 交易设置
  - `confidence_threshold`: 信心度阈值（0-1），低于此值的交易不执行
  - `max_positions`: 最大持仓数
  - `leverage_range`: 杠杆范围
  - `position_size_range`: 仓位大小范围

### 3. 自定义提示词

可以修改 `prompts/` 目录下的文件来自定义AI提示词：

- `user_instruction.txt`: 定义AI的角色、交易规则和返回格式
- `suffix.txt`: 提示词的结束部分

## 使用方法

### 单次运行模式

运行一次交易周期，获取数据、查询AI、执行交易后退出：

```bash
python main.py --mode single
```

### 持续运行模式

系统会持续运行，每隔指定时间执行一次交易周期：

```bash
# 每3分钟运行一次（默认）
python main.py --mode continuous --interval 3

# 每5分钟运行一次
python main.py --mode continuous --interval 5
```

### 使用自定义配置文件

```bash
python main.py --config my_config.json --mode continuous
```

### 停止系统

在持续运行模式下，按 `Ctrl+C` 可以优雅地停止系统。

## 工作流程

1. **数据获取**
   - 获取配置中所有交易对的K线数据
   - 计算短期和长期技术指标
   - 获取持仓量和资金费率
   - 获取账户余额和当前仓位

2. **AI决策**
   - 生成包含运行状态的提示词前缀
   - 整合市场数据和账户数据
   - 并行查询所有配置的AI模型
   - 比较各AI的建议，只保留完全一致的交易

3. **交易执行**
   - 过滤低信心度的交易
   - 检查亏损仓位，防止在亏损时平仓
   - 执行开仓：设置杠杆、下单、设置止损
   - 执行平仓：撤销止损单、平仓
   - 记录执行结果

## AI交易建议格式

AI返回的JSON格式：

```json
{
    "analysis": "市场分析文本",
    "trades": [
        {
            "action": "OPEN",
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "leverage": 10,
            "position_size_percent": 0.08,
            "entry_price_target": 115000,
            "stop_loss": 113500,
            "confidence": 0.75,
            "reason": "技术指标显示强烈买入信号"
        }
    ]
}
```

**动作类型：**
- `OPEN`: 开新仓位
- `CLOSE`: 平仓现有仓位
- `HOLD`: 持有现有仓位
- `BP`: 突破买入
- `SP`: 突破卖出

## 安全特性

1. **信心度过滤**: 只执行信心度高于阈值的交易
2. **多AI共识**: 只有所有AI意见一致时才执行交易
3. **止损保护**: 每次开仓自动设置止损单
4. **亏损保护**: 不在亏损状态下平仓（除非止损触发）
5. **测试网支持**: 可以先在测试网上运行验证

## 注意事项

1. **风险警告**: 加密货币交易存在高风险，可能导致资金损失。本系统仅供学习和研究使用，使用前请充分测试。

2. **API密钥安全**: 
   - 不要将包含真实API密钥的配置文件提交到版本控制系统
   - 使用环境变量或密钥管理服务存储敏感信息
   - 建议使用只读API密钥或限制权限的API密钥

3. **测试建议**:
   - 先在测试网上运行系统
   - 使用小额资金进行测试
   - 逐步增加交易对和仓位大小

4. **监控**:
   - 定期检查系统日志
   - 监控账户余额和仓位
   - 关注AI决策质量

5. **网络要求**:
   - 需要稳定的网络连接
   - 建议在服务器上运行以保证稳定性

## 扩展和定制

### 添加新的交易所

修改 `data_fetcher.py` 和 `trading_executor.py`，适配新交易所的API。

### 添加新的技术指标

在 `data_fetcher.py` 的 `calculate_indicators` 方法中添加新指标。

### 使用其他AI模型

只要API符合OpenAI格式，可以直接在配置文件中添加。对于其他格式的API，需要修改 `ai_decision.py` 的 `query_ai` 方法。

### 自定义交易逻辑

修改 `trading_executor.py` 中的执行逻辑，如添加新的订单类型、调整仓位管理策略等。

## 故障排除

### TA-Lib安装失败

确保先安装了TA-Lib的C库，然后再安装Python包。参考安装部分的说明。

### API连接失败

- 检查网络连接
- 确认API密钥正确
- 检查是否使用了正确的API端点（测试网/主网）

### AI响应格式错误

- 检查提示词是否正确
- 查看AI返回的原始内容
- 可能需要调整提示词让AI更严格地遵循JSON格式

## 许可证

本项目仅供学习和研究使用。使用者需自行承担交易风险。

## 联系方式

如有问题或建议，请通过GitHub Issues反馈。
