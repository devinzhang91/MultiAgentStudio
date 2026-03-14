"""
股票分析工作室模板
研究分析型团队，专注于股票和投资分析
"""

from typing import List, Dict, Any

from .base import StudioTemplate, AgentConfig, load_template_agents


class StockAnalysisTemplate(StudioTemplate):
    """股票分析工作室"""
    
    name = "股票分析工作室"
    description = "专业投资研究团队，包含首席分析师、宏观研究员、行业研究员、技术分析师和风险评估师，采用去中心化协作模式共享研究成果，提供全面的投资决策支持"
    default_architecture = "decentralized"
    
    def get_agents(self) -> List[AgentConfig]:
        """返回股票分析团队的Agent配置"""
        return load_template_agents("stock_analysis")
    
    def get_agent_to_agent_config(self) -> Dict[str, Any]:
        """返回agentToAgent配置 - 去中心化模式允许所有agent间通信"""
        agent_ids = [a.id for a in self.get_agents()]
        return {
            "enabled": True,
            "allow": agent_ids,
            "historyLimit": 100  # 去中心化模式下更大的历史记录
        }
