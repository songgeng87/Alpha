"""
AI决策模块
支持多个AI模型进行交易决策，汇总建议并确保一致性
"""
import requests
import json
from typing import Dict, List, Optional
from pathlib import Path


class AIDecision:
    """AI决策类，负责调用多个AI模型并汇总交易建议"""
    
    def __init__(self, ai_models: List[Dict], prompt_dir: str = "prompts"):
        """
        初始化AI决策器
        
        Args:
            ai_models: AI模型配置列表
            prompt_dir: 提示词文件目录
        """
        self.ai_models = ai_models
        self.prompt_dir = Path(prompt_dir)
        
        # 加载提示词模板
        self.user_instruction = self._load_prompt("user_instruction.txt")
        self.suffix = self._load_prompt("suffix.txt")
    
    def _load_prompt(self, filename: str) -> str:
        """
        从文件加载提示词
        
        Args:
            filename: 提示词文件名
            
        Returns:
            提示词内容
        """
        try:
            filepath = self.prompt_dir / filename
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"加载提示词文件失败 {filename}: {e}")
            return ""
    
    def build_prompt(self, prefix: str, market_data: str, account_data: str) -> str:
        """
        构建完整的提示词
        
        Args:
            prefix: 前缀部分（包含运行时间、调用次数等）
            market_data: 市场数据
            account_data: 账户数据
            
        Returns:
            完整的提示词
        """
        prompt = f"{prefix}\n\n"
        prompt += market_data
        prompt += account_data
        prompt += f"\n{self.suffix}\n"
        
        return prompt
    
    def query_ai(self, ai_config: Dict, system_prompt: str, user_prompt: str) -> Optional[Dict]:
        """
        查询单个AI模型
        
        Args:
            ai_config: AI配置信息
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            AI返回的交易建议（JSON格式）
        """
        api_url = ai_config['api_url']
        api_key = ai_config['api_key']
        model = ai_config['model']
        ai_name = ai_config['name']
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 2000
        }
        
        try:
            print(f"\n正在查询 {ai_name}...")
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 尝试解析JSON
            # 去除可能的markdown代码块标记
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            decision = json.loads(content)
            print(f"{ai_name} 返回建议成功")
            return decision
            
        except json.JSONDecodeError as e:
            print(f"{ai_name} 返回的JSON格式无效: {e}")
            print(f"原始内容: {content}")
            return None
        except Exception as e:
            print(f"查询 {ai_name} 失败: {e}")
            return None
    
    def query_all_ais(self, prefix: str, market_data: str, account_data: str) -> List[Dict]:
        """
        查询所有AI模型
        
        Args:
            prefix: 提示词前缀
            market_data: 市场数据
            account_data: 账户数据
            
        Returns:
            所有AI的决策列表
        """
        user_prompt = self.build_prompt(prefix, market_data, account_data)
        system_prompt = self.user_instruction
        
        all_decisions = []
        
        for ai_config in self.ai_models:
            decision = self.query_ai(ai_config, system_prompt, user_prompt)
            if decision:
                decision['ai_name'] = ai_config['name']
                all_decisions.append(decision)
        
        return all_decisions
    
    def normalize_trade_action(self, trade: Dict) -> tuple:
        """
        标准化交易动作，用于比较
        
        Args:
            trade: 交易建议
            
        Returns:
            (action, symbol, direction) 元组
        """
        action = trade.get('action', '').upper()
        symbol = trade.get('symbol', '').upper()
        direction = trade.get('direction', '').upper() if action != 'HOLD' else ''
        
        return (action, symbol, direction)
    
    def merge_decisions(self, all_decisions: List[Dict]) -> List[Dict]:
        """
        合并多个AI的决策，只保留完全一致的交易建议
        
        Args:
            all_decisions: 所有AI的决策列表
            
        Returns:
            最终的交易建议列表
        """
        if not all_decisions:
            print("没有AI返回有效决策")
            return []
        
        if len(all_decisions) == 1:
            print("只有一个AI返回决策，直接使用其建议")
            return all_decisions[0].get('trades', [])
        
        # 提取所有交易建议
        all_trades = []
        for decision in all_decisions:
            trades = decision.get('trades', [])
            ai_name = decision.get('ai_name', 'Unknown')
            for trade in trades:
                trade['from_ai'] = ai_name
                all_trades.append(trade)
        
        # 按交易对分组
        trades_by_symbol = {}
        for trade in all_trades:
            symbol = trade.get('symbol', '').upper()
            if symbol not in trades_by_symbol:
                trades_by_symbol[symbol] = []
            trades_by_symbol[symbol].append(trade)
        
        # 对每个交易对，检查所有AI是否给出一致建议
        final_trades = []
        
        for symbol, trades in trades_by_symbol.items():
            print(f"\n分析 {symbol} 的建议...")
            
            # 获取所有标准化的动作
            normalized_actions = [self.normalize_trade_action(t) for t in trades]
            
            # 检查是否所有建议都一致
            if len(set(normalized_actions)) == 1:
                # 所有AI建议一致，使用第一个AI的详细参数
                action, _, direction = normalized_actions[0]
                print(f"  所有AI对 {symbol} 的建议一致: {action} {direction}")
                
                # 使用第一个决策的参数
                first_trade = trades[0].copy()
                
                # 添加信心度（可以取平均值或最小值）
                confidences = [t.get('confidence', 0.5) for t in trades]
                first_trade['confidence'] = sum(confidences) / len(confidences)
                
                # 记录有多少AI同意
                first_trade['ai_consensus'] = len(trades)
                first_trade['total_ais'] = len(self.ai_models)
                
                final_trades.append(first_trade)
            else:
                # AI建议不一致
                print(f"  AI对 {symbol} 的建议不一致:")
                for trade in trades:
                    action, _, direction = self.normalize_trade_action(trade)
                    ai_name = trade.get('from_ai', 'Unknown')
                    print(f"    {ai_name}: {action} {direction}")
                print(f"  跳过 {symbol} 的交易")
        
        print(f"\n最终生成 {len(final_trades)} 个一致的交易建议")
        return final_trades
    
    def get_trading_decision(self, prefix: str, market_data: str, 
                            account_data: str) -> Dict:
        """
        获取最终的交易决策
        
        Args:
            prefix: 提示词前缀
            market_data: 市场数据
            account_data: 账户数据
            
        Returns:
            包含分析和交易建议的字典
        """
        # 查询所有AI
        all_decisions = self.query_all_ais(prefix, market_data, account_data)
        
        if not all_decisions:
            return {
                'analysis': '未能获取AI决策',
                'trades': []
            }
        
        # 合并决策
        merged_trades = self.merge_decisions(all_decisions)
        
        # 汇总分析
        analyses = [d.get('analysis', '') for d in all_decisions]
        combined_analysis = "\n\n".join([
            f"{d.get('ai_name', 'AI')}: {d.get('analysis', '')}" 
            for d in all_decisions
        ])
        
        return {
            'analysis': combined_analysis,
            'trades': merged_trades,
            'ai_count': len(all_decisions),
            'consensus_count': len(merged_trades)
        }


if __name__ == "__main__":
    # 测试代码
    test_ai_models = [
        {
            'name': 'Test-GPT',
            'api_url': 'https://api.openai.com/v1/chat/completions',
            'api_key': 'test-key',
            'model': 'gpt-4'
        }
    ]
    
    ai_decision = AIDecision(test_ai_models)
    
    test_prefix = "Test session at 2025-10-31"
    test_market = "BTC Price: 115000"
    test_account = "Available Cash: 10000"
    
    print("AI决策模块已初始化")
    print(f"加载的提示词长度: {len(ai_decision.user_instruction)} 字符")
