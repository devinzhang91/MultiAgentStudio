"""
超级软件工程工作室模板
完整软件工程团队，支持从需求到部署的全流程
"""

from typing import List, Dict, Any

from .base import StudioTemplate, AgentConfig, load_template_agents


class SoftwareEngineeringTemplate(StudioTemplate):
    """超级软件工程工作室"""
    
    name = "超级软件工程工作室"
    description = "完整软件工程团队，包含项目经理、UI/UX设计师、开发工程师、测试工程师、DevOps工程师和技术文档工程师，支持从需求到部署的全流程开发"
    default_architecture = "hybrid"
    
    def get_agents(self) -> List[AgentConfig]:
        """返回软件工程团队的Agent配置"""
        return load_template_agents("software_engineering")
    
    def get_agent_to_agent_config(self) -> Dict[str, Any]:
        """返回agentToAgent配置"""
        agent_ids = [a.id for a in self.get_agents()]
        return {
            "enabled": True,
            "allow": agent_ids,
            "historyLimit": 50
        }
