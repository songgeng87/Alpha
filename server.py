"""
AI交易建议API服务
提供HTTP API接口，根据用户指定的交易对和时间周期返回AI交易建议
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from pathlib import Path
from typing import Dict, List
from data_fetcher import DataFetcher
from ai_decision import AIDecision
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

app = Flask(__name__, static_folder='web', static_url_path='')
CORS(app)  # 允许跨域请求

# 加载配置
config_path = Path(__file__).parent / "config.json"
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)


def get_ai_advice(symbols: List[str], short_interval: str, long_interval: str, 
                  kline_limit: int = 1000) -> Dict:
    """
    获取AI交易建议
    
    Args:
        symbols: 交易对列表，例如 ["BTCUSDT", "ETHUSDT"]
        short_interval: 短期时间周期，例如 "3m", "5m", "15m"
        long_interval: 长期时间周期，例如 "1h", "4h", "1d"
        kline_limit: K线数量限制
        
    Returns:
        包含AI建议的字典
    """
    try:
        # 初始化数据获取器
        data_fetcher = DataFetcher(
            config['exchange'],
            skip_latest_candle=config.get('data_settings', {}).get('skip_latest_candle', False)
        )
        
        # 构建交易对配置
        trading_pairs = [
            {
                'symbol': symbol,
                'short_interval': short_interval,
                'long_interval': long_interval,
                'kline_limit': kline_limit
            }
            for symbol in symbols
        ]
        
        # 获取市场数据
        market_data = data_fetcher.get_all_market_data(trading_pairs)
        
        if not market_data:
            return {
                'success': False,
                'error': '无法获取市场数据'
            }
        
        # 构建账户数据（假设无持仓，用于查询模式）
        account_data = """
============================================================
账户信息（查询模式 - 假设无持仓）
============================================================

可用资金: 10000.0 USDT
当前持仓: 无
"""
        
        # 初始化AI决策器
        ai_decision = AIDecision(config['ai_models'])
        
        # 生成提示词前缀
        prefix = f"""您正在分析以下交易对的市场数据。
时间周期: 短期={short_interval}, 长期={long_interval}
分析模式: 纯建议查询（假设无持仓）

请根据技术指标给出专业的交易建议。
"""
        
        # 查询所有AI
        decisions = ai_decision.query_all_ais(prefix, market_data, account_data)
        
        if not decisions:
            return {
                'success': False,
                'error': '所有AI模型均未返回有效决策'
            }
        
        # 返回结果
        return {
            'success': True,
            'symbols': symbols,
            'short_interval': short_interval,
            'long_interval': long_interval,
            'ai_count': len(decisions),
            'decisions': decisions
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'处理请求时出错: {str(e)}'
        }


@app.route('/')
def index():
    """返回前端页面"""
    return app.send_static_file('index.html')


@app.route('/api/get_advice', methods=['POST'])
def api_get_advice():
    """
    获取AI交易建议的API端点
    
    请求格式:
    {
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "short_interval": "3m",
        "long_interval": "4h",
        "kline_limit": 1000  // 可选，默认1000
    }
    
    响应格式:
    {
        "success": true,
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "short_interval": "3m",
        "long_interval": "4h",
        "ai_count": 1,
        "decisions": [
            {
                "ai_name": "DeepSeek",
                "analysis": "市场分析...",
                "trades": [...]
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        # 验证必需参数
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        symbols = data.get('symbols', [])
        short_interval = data.get('short_interval')
        long_interval = data.get('long_interval')
        kline_limit = data.get('kline_limit', 1000)
        
        # 参数验证
        if not symbols:
            return jsonify({
                'success': False,
                'error': 'symbols参数不能为空'
            }), 400
        
        if not isinstance(symbols, list):
            return jsonify({
                'success': False,
                'error': 'symbols必须是数组'
            }), 400
        
        if not short_interval:
            return jsonify({
                'success': False,
                'error': '缺少short_interval参数'
            }), 400
        
        if not long_interval:
            return jsonify({
                'success': False,
                'error': '缺少long_interval参数'
            }), 400
        
        # 验证时间周期格式
        valid_intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
        if short_interval not in valid_intervals:
            return jsonify({
                'success': False,
                'error': f'short_interval无效，支持的值: {", ".join(valid_intervals)}'
            }), 400
        
        if long_interval not in valid_intervals:
            return jsonify({
                'success': False,
                'error': f'long_interval无效，支持的值: {", ".join(valid_intervals)}'
            }), 400
        
        # 获取AI建议
        result = get_ai_advice(symbols, short_interval, long_interval, kline_limit)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/available_symbols', methods=['GET'])
def api_available_symbols():
    """
    获取可用的交易对列表
    """
    try:
        symbols = [pair['symbol'] for pair in config.get('trading_pairs', [])]
        return jsonify({
            'success': True,
            'symbols': symbols
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'service': 'AI Trading Advice API'
    }), 200


if __name__ == '__main__':
    # 从环境变量读取配置
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('API_DEBUG', 'False').lower() == 'true'
    
    print("="*60)
    print("AI交易建议API服务")
    print("="*60)
    print(f"服务地址: http://{host}:{port}")
    print(f"API文档: http://{host}:{port}/api/health")
    print(f"前端页面: http://{host}:{port}/")
    print("="*60)
    
    app.run(host=host, port=port, debug=debug)
