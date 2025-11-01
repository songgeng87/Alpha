"""
AI决策模块
支持多个AI模型进行交易决策,汇总建议并确保一致性
"""
import requests
import json
import time
from typing import Dict, List, Optional
from pathlib import Path
import os
from datetime import datetime


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
        
        # 创建AI交互历史目录
        self.history_dir = Path("ai_history")
        self.history_dir.mkdir(exist_ok=True)
    
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
    
    def _save_ai_interaction(self, model_name: str, system_prompt: str, 
                            user_prompt: str, ai_response: str, success: bool = True):
        """
        保存AI交互历史
        
        Args:
            model_name: AI模型名称
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            ai_response: AI回答
            success: 是否成功获取回答
        """
        try:
            timestamp = datetime.now()
            filename = timestamp.strftime("%Y%m%d_%H%M%S") + f"_{model_name}.json"
            filepath = self.history_dir / filename
            
            interaction_data = {
                "timestamp": timestamp.isoformat(),
                "model_name": model_name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "ai_response": ai_response,
                "success": success
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(interaction_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存AI交互历史失败: {e}")
    
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
    
    def query_ai(self, prompt: str, model_config: Dict) -> str:
        """调用单个AI模型进行决策（带重试机制和异常隔离）"""
        api_key = model_config.get("api_key")
        api_key_env = model_config.get("api_key_env")
        if not api_key and api_key_env:
            api_key = os.getenv(api_key_env)
        if not api_key:
            print(f"缺少API Key，无法调用模型 {model_config.get('name', 'unknown')}")
            return "{}"
            
        # 兼容 url 和 api_url 两种配置方式
        url = model_config.get("url") or model_config.get("api_url")
        if not url:
            print(f"缺少API URL，无法调用模型 {model_config.get('name', 'unknown')}")
            return "{}"
            
        model = model_config["model"]
        model_name = model_config.get("name", model)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": self.user_instruction},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }

        max_retries = 3
        retry_delay = 2
        timeout = 60
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
                response.raise_for_status()
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    ai_response = result["choices"][0]["message"]["content"]
                    # 保存成功的交互历史
                    self._save_ai_interaction(
                        model_name=model_name,
                        system_prompt=self.user_instruction,
                        user_prompt=prompt,
                        ai_response=ai_response,
                        success=True
                    )
                    return ai_response
                else:
                    print(f"AI响应格式异常 [{model_name}]: {result}")
                    self._save_ai_interaction(
                        model_name=model_name,
                        system_prompt=self.user_instruction,
                        user_prompt=prompt,
                        ai_response=json.dumps(result),
                        success=False
                    )
                    return "{}"
                    
            except requests.exceptions.Timeout:
                print(f"AI查询超时 [{model_name}] (尝试 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
                else:
                    self._save_ai_interaction(
                        model_name=model_name,
                        system_prompt=self.user_instruction,
                        user_prompt=prompt,
                        ai_response="TIMEOUT_ERROR",
                        success=False
                    )
                    return "{}"
                    
            except requests.exceptions.RequestException as e:
                print(f"AI查询网络错误 [{model_name}] (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    self._save_ai_interaction(
                        model_name=model_name,
                        system_prompt=self.user_instruction,
                        user_prompt=prompt,
                        ai_response=f"NETWORK_ERROR: {str(e)}",
                        success=False
                    )
                    return "{}"
                    
            except json.JSONDecodeError as e:
                print(f"AI响应JSON解析失败 [{model_name}]: {e}")
                self._save_ai_interaction(
                    model_name=model_name,
                    system_prompt=self.user_instruction,
                    user_prompt=prompt,
                    ai_response=f"JSON_DECODE_ERROR: {str(e)}",
                    success=False
                )
                return "{}"
                
            except Exception as e:
                print(f"AI查询失败 [{model_name}]: {e}")
                self._save_ai_interaction(
                    model_name=model_name,
                    system_prompt=self.user_instruction,
                    user_prompt=prompt,
                    ai_response=f"UNKNOWN_ERROR: {str(e)}",
                    success=False
                )
                return "{}"
        
        return "{}"
    
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
        
        all_decisions = []
        
        for ai_config in self.ai_models:
            response_str = self.query_ai(user_prompt, ai_config)
            if response_str and response_str != "{}":
                try:
                    # 清理可能的markdown代码块标记
                    cleaned_response = response_str.strip()
                    if cleaned_response.startswith("```json"):
                        cleaned_response = cleaned_response[7:]  # 移除开头的```json
                    elif cleaned_response.startswith("```"):
                        cleaned_response = cleaned_response[3:]  # 移除开头的```
                    if cleaned_response.endswith("```"):
                        cleaned_response = cleaned_response[:-3]  # 移除结尾的```
                    cleaned_response = cleaned_response.strip()
                    
                    decision = json.loads(cleaned_response)
                    decision['ai_name'] = ai_config['name']
                    all_decisions.append(decision)
                except json.JSONDecodeError as e:
                    print(f"解析AI响应失败 [{ai_config.get('name')}]: {e}")
                    print(f"响应内容: {response_str[:200]}")
        
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
