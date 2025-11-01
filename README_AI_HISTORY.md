# AI交互历史说明

## 功能概述

系统会自动记录每次与AI模型的交互历史，包括：
- 系统提示词（system prompt）
- 用户提示词（user prompt，包含市场数据和账户信息）
- AI的回答
- 调用时间戳
- 是否成功获取回答

## 存储位置

所有AI交互历史保存在 `ai_history/` 目录下。

## 文件命名规则

```
YYYYMMDD_HHMMSS_模型名称.json
```

示例：
- `20250101_143025_DeepSeek.json`
- `20250101_143026_GPT4.json`

## 文件格式

每个JSON文件包含以下字段：

```json
{
  "timestamp": "2025-01-01T14:30:25.123456",
  "model_name": "DeepSeek",
  "system_prompt": "你是一个专业的数字货币合约交易员...",
  "user_prompt": "当前运行信息：...\n\n市场数据：...\n\n账户数据：...",
  "ai_response": "{\"analysis\": \"...\", \"trades\": [...]}",
  "success": true
}
```

### 字段说明

- `timestamp`: ISO格式的时间戳
- `model_name`: AI模型名称
- `system_prompt`: 系统提示词（交易员角色设定和JSON格式要求）
- `user_prompt`: 完整的用户输入（包含运行信息、市场数据、账户数据）
- `ai_response`: AI的回答内容（成功时为JSON格式的交易建议，失败时为错误信息）
- `success`: 布尔值，表示是否成功获取有效回答

## 失败记录

当AI调用失败时，`ai_response` 字段会记录错误类型：

- `TIMEOUT_ERROR`: 请求超时
- `NETWORK_ERROR: <详情>`: 网络错误
- `JSON_DECODE_ERROR: <详情>`: JSON解析失败
- `UNKNOWN_ERROR: <详情>`: 未知错误

## 使用场景

1. **调试分析**: 回溯AI的决策过程，分析决策质量
2. **性能评估**: 统计AI响应时间和成功率
3. **策略优化**: 分析哪些市场条件下AI给出更好的建议
4. **审计追溯**: 记录所有交易决策的完整依据

## 注意事项

- 历史文件包含敏感的账户信息和市场数据，请妥善保管
- `.gitignore` 已配置忽略 `ai_history/` 目录，不会提交到版本控制
- 建议定期清理或归档历史文件，避免占用过多磁盘空间
- 可以编写脚本分析历史数据，提取统计信息
