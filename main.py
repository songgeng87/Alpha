"""
主程序
协调数据获取、AI决策和交易执行的工作流程
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from data_fetcher import DataFetcher
from ai_decision import AIDecision
from trading_executor import TradingExecutor


class TradingSystem:
    """自动交易系统主控制类"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化交易系统
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # 系统状态
        self.start_time = None
        self.invocation_count = 0
        self.invocation_count_file = self.config['system'].get(
            'invocation_count_file', 'invocation_count.txt'
        )
        
        # 初始化各模块
        self.data_fetcher = DataFetcher(self.config['exchange'])
        self.ai_decision = AIDecision(
            self.config['ai_models'],
            prompt_dir='prompts'
        )
        self.trading_executor = TradingExecutor(
            self.config['exchange'],
            confidence_threshold=self.config['trading_settings']['confidence_threshold']
        )
        
        # 加载或初始化系统状态
        self._load_system_state()
    
    def _load_config(self) -> Dict:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"配置文件加载成功: {self.config_path}")
            return config
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            raise
    
    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def _load_system_state(self):
        """加载系统状态"""
        # 加载开始时间
        if self.config['system']['start_time']:
            self.start_time = datetime.fromisoformat(self.config['system']['start_time'])
        else:
            self.start_time = datetime.now()
            self.config['system']['start_time'] = self.start_time.isoformat()
            self._save_config()
        
        # 加载调用次数
        try:
            if Path(self.invocation_count_file).exists():
                with open(self.invocation_count_file, 'r') as f:
                    self.invocation_count = int(f.read().strip())
            else:
                self.invocation_count = 0
        except Exception as e:
            print(f"加载调用次数失败: {e}")
            self.invocation_count = 0
    
    def _save_invocation_count(self):
        """保存调用次数"""
        try:
            with open(self.invocation_count_file, 'w') as f:
                f.write(str(self.invocation_count))
        except Exception as e:
            print(f"保存调用次数失败: {e}")
    
    def _generate_prompt_prefix(self) -> str:
        """
        生成提示词前缀
        
        Returns:
            前缀文本
        """
        current_time = datetime.now()
        elapsed_time = current_time - self.start_time
        elapsed_minutes = int(elapsed_time.total_seconds() / 60)
        
        prefix = f"It has been {elapsed_minutes} minutes since you started trading. "
        prefix += f"The current time is {current_time} and you've been invoked "
        prefix += f"{self.invocation_count} times. "
        prefix += "Below, we are providing you with a variety of state data, price data, "
        prefix += "and predictive signals so you can discover alpha. "
        prefix += "Below that is your current account information, value, performance, positions, etc.\n\n"
        prefix += "ALL OF THE PRICE OR SIGNAL DATA BELOW IS ORDERED: OLDEST → NEWEST\n\n"
        prefix += "Timeframes note: Unless stated otherwise in a section title, intraday series "
        prefix += "are provided at the configured intervals. If a coin uses a different interval, "
        prefix += "it is explicitly stated in that section.\n"
        
        return prefix
    
    def run_single_cycle(self) -> Dict:
        """
        运行单次交易周期
        
        Returns:
            周期执行结果
        """
        print("\n" + "="*80)
        print(f"开始交易周期 #{self.invocation_count + 1}")
        print(f"时间: {datetime.now()}")
        print("="*80 + "\n")
        
        # 增加调用次数
        self.invocation_count += 1
        self._save_invocation_count()
        
        # 1. 获取市场数据
        print("步骤 1: 获取市场数据...")
        market_data = self.data_fetcher.get_all_market_data(
            self.config['trading_pairs']
        )
        
        if not market_data:
            print("获取市场数据失败，跳过本周期")
            return {'status': 'failed', 'reason': 'no_market_data'}
        
        # 2. 获取账户数据
        print("\n步骤 2: 获取账户数据...")
        account_data_dict = self.data_fetcher.get_account_data()
        account_data = self.data_fetcher.format_account_data(account_data_dict)
        available_cash = account_data_dict.get('available_cash', 0)
        
        # 3. 生成提示词前缀
        print("\n步骤 3: 生成提示词前缀...")
        prefix = self._generate_prompt_prefix()
        
        # 4. 查询AI获取决策
        print("\n步骤 4: 查询AI获取交易决策...")
        decision = self.ai_decision.get_trading_decision(
            prefix, market_data, account_data
        )
        
        print(f"\nAI分析:")
        print(decision.get('analysis', '无分析'))
        print(f"\n共收到 {decision.get('ai_count', 0)} 个AI响应")
        print(f"达成共识的交易建议: {decision.get('consensus_count', 0)} 个")
        
        trades = decision.get('trades', [])
        
        if not trades:
            print("\n没有需要执行的交易")
            return {
                'status': 'success',
                'trades_count': 0,
                'executed': 0
            }
        
        # 5. 执行交易
        print("\n步骤 5: 执行交易...")
        for i, trade in enumerate(trades, 1):
            print(f"\n交易建议 {i}:")
            print(f"  交易对: {trade.get('symbol')}")
            print(f"  动作: {trade.get('action')}")
            print(f"  方向: {trade.get('direction', 'N/A')}")
            print(f"  杠杆: {trade.get('leverage', 'N/A')}")
            print(f"  仓位大小: {trade.get('position_size_percent', 0)*100:.1f}%")
            print(f"  信心度: {trade.get('confidence', 0):.2f}")
            print(f"  理由: {trade.get('reason', 'N/A')}")
        
        execution_results = self.trading_executor.execute_trades(
            trades, available_cash
        )
        
        # 6. 输出执行结果
        print("\n" + "="*80)
        print("执行结果:")
        print(f"  总交易数: {execution_results['total']}")
        print(f"  成功执行: {execution_results['executed']}")
        print(f"  信心度不足跳过: {execution_results['skipped_low_confidence']}")
        print(f"  执行失败: {execution_results['failed']}")
        print("="*80 + "\n")
        
        # 显示当前仓位
        print(self.trading_executor.get_active_positions_summary())
        
        return {
            'status': 'success',
            'trades_count': execution_results['total'],
            'executed': execution_results['executed'],
            'skipped': execution_results['skipped_low_confidence'],
            'failed': execution_results['failed']
        }
    
    def run_continuous(self, interval_minutes: int = 3):
        """
        持续运行交易系统
        
        Args:
            interval_minutes: 运行间隔（分钟）
        """
        print("\n" + "="*80)
        print("启动自动交易系统")
        print(f"运行间隔: {interval_minutes} 分钟")
        print(f"信心阈值: {self.trading_executor.confidence_threshold}")
        print(f"监控交易对: {[p['symbol'] for p in self.config['trading_pairs']]}")
        print(f"使用AI模型: {[m['name'] for m in self.config['ai_models']]}")
        print("="*80 + "\n")
        
        try:
            while True:
                try:
                    result = self.run_single_cycle()
                    
                    if result['status'] == 'success':
                        print(f"\n周期完成，等待 {interval_minutes} 分钟...")
                    else:
                        print(f"\n周期失败: {result.get('reason', 'unknown')}")
                    
                except Exception as e:
                    print(f"\n周期执行出错: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 等待下一个周期
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\n\n收到中断信号，正在停止系统...")
            print("="*80)
            print("系统已停止")
            print(f"总运行时间: {datetime.now() - self.start_time}")
            print(f"总调用次数: {self.invocation_count}")
            print("="*80)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI驱动的数字货币自动交易系统')
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='配置文件路径 (默认: config.json)'
    )
    parser.add_argument(
        '--mode',
        type=str,
        choices=['single', 'continuous'],
        default='continuous',
        help='运行模式: single=运行一次, continuous=持续运行 (默认: continuous)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=3,
        help='持续运行模式下的间隔时间（分钟，默认: 3）'
    )
    
    args = parser.parse_args()
    
    # 初始化系统
    system = TradingSystem(config_path=args.config)
    
    # 运行系统
    if args.mode == 'single':
        print("运行模式: 单次执行")
        result = system.run_single_cycle()
        print(f"\n执行完成: {result}")
    else:
        print("运行模式: 持续运行")
        system.run_continuous(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
