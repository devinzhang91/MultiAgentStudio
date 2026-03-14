"""
Remotion视频工作室模板
专注于视频内容创作和Remotion代码视频生成
"""

from typing import List, Dict, Any

from .base import StudioTemplate, AgentConfig, load_template_agents


class RemotionVideoTemplate(StudioTemplate):
    """Remotion视频工作室"""
    
    name = "Remotion视频工作室"
    description = "专业视频创作团队，包含视频导演、脚本编剧、视觉设计师、Remotion开发专员、配音专员和后期剪辑师，专注于代码视频和创意视频内容制作"
    default_architecture = "hybrid"
    
    def get_agents(self) -> List[AgentConfig]:
        """返回视频工作室的Agent配置"""
        return load_template_agents("remotion_video")
    
    def get_agent_to_agent_config(self) -> Dict[str, Any]:
        """返回agentToAgent配置"""
        agent_ids = [a.id for a in self.get_agents()]
        return {
            "enabled": True,
            "allow": agent_ids,
            "historyLimit": 50
        }
