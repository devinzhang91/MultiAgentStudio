"""
股票分析工作室模板
研究分析型团队，专注于股票和投资分析
"""

from typing import List, Dict, Any
from .base import StudioTemplate, AgentConfig


class StockAnalysisTemplate(StudioTemplate):
    """股票分析工作室"""
    
    name = "股票分析工作室"
    description = "专业投资研究团队，包含首席分析师、宏观研究员、行业研究员、技术分析师和风险评估师，采用去中心化协作模式共享研究成果，提供全面的投资决策支持"
    default_architecture = "decentralized"
    
    def get_agents(self) -> List[AgentConfig]:
        """返回股票分析团队的Agent配置"""
        return [
            AgentConfig(
                id="lead-analyst",
                employee_id="emp-lead-analyst",
                name="Warren Buffett",
                display_name="Warren",
                role="首席分析师 | 主脑协调",
                agent_type="main_brain",
                is_main_brain=True,
                emoji="📊",
                avatar="📊",
                personality="价值投资理念的投资大师，拥有深厚的财务分析功底和长期投资视野。善于从基本面出发发现被低估的优质资产，决策理性且坚持自己的投资原则。",
                specialty="价值投资、基本面分析、投资组合管理、长期策略制定、团队研究协调",
                allowed_tools=["sessions_send", "sessions_list", "read", "write", "browser", "exec"],
                denied_tools=[],
                model="volcengine/glm-4.7",
            ),
            AgentConfig(
                id="macro-researcher",
                employee_id="emp-macro-researcher",
                name="Ray Dalio",
                display_name="Ray",
                role="宏观研究员",
                agent_type="specialist",
                is_main_brain=False,
                emoji="🏛️",
                avatar="🏛️",
                personality="全球宏观视野的经济学家，擅长分析宏观经济周期和货币政策对市场的影响。善于发现经济趋势中的投资机会和风险信号。",
                specialty="宏观经济分析、货币政策研究、经济周期判断、全球市场趋势、地缘政治影响",
                allowed_tools=["browser", "read", "write", "edit", "exec"],
                denied_tools=["apply_patch"],
                model="volcengine/glm-4.7",
            ),
            AgentConfig(
                id="sector-researcher",
                employee_id="emp-sector-researcher",
                name="Peter Lynch",
                display_name="Peter",
                role="行业研究员",
                agent_type="specialist",
                is_main_brain=False,
                emoji="🏭",
                avatar="🏭",
                personality="深入一线的行业专家，相信\"了解你所投资的公司\"。擅长深入调研行业发展趋势、竞争格局和商业模式，发现十倍股的早期信号。",
                specialty="行业分析、竞争格局研究、商业模式评估、公司调研、产业链分析",
                allowed_tools=["browser", "read", "write", "edit", "exec"],
                denied_tools=["apply_patch"],
                model="volcengine/glm-4.7",
            ),
            AgentConfig(
                id="technical-analyst",
                employee_id="emp-technical-analyst",
                name="Paul Tudor Jones",
                display_name="Paul",
                role="技术分析师",
                agent_type="specialist",
                is_main_brain=False,
                emoji="📈",
                avatar="📈",
                personality="技术分析大师，善于通过图表和指标把握市场情绪和价格趋势。结合量化分析方法，精准把握入场和出场时机。",
                specialty="技术分析、图表模式识别、量化指标、市场情绪分析、交易系统设计",
                allowed_tools=["browser", "exec", "read", "write", "edit"],
                denied_tools=["apply_patch"],
                model="volcengine/glm-4.7",
            ),
            AgentConfig(
                id="risk-assessor",
                employee_id="emp-risk-assessor",
                name="Nassim Taleb",
                display_name="Nassim",
                role="风险评估师",
                agent_type="specialist",
                is_main_brain=False,
                emoji="⚠️",
                avatar="⚠️",
                personality="风险管理思想家，对极端事件和尾部风险有深刻洞察。善于发现潜在的风险因素，构建反脆弱的投资组合。",
                specialty="风险评估、尾部风险管理、压力测试、组合风险分析、黑天鹅事件预警",
                allowed_tools=["exec", "read", "write", "browser"],
                denied_tools=["apply_patch", "edit"],
                model="volcengine/glm-4.7",
            ),
        ]
    
    def get_agent_to_agent_config(self) -> Dict[str, Any]:
        """返回agentToAgent配置 - 去中心化模式允许所有agent间通信"""
        agent_ids = [a.id for a in self.get_agents()]
        return {
            "enabled": True,
            "allow": agent_ids,
            "historyLimit": 100  # 去中心化模式下更大的历史记录
        }
