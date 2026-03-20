"""
Remotion视频工作室模板
专注于视频内容创作和Remotion代码视频生成

Skills说明：
- Skills预置在 data/agents-docs/remotion_video/{agent_id}/skills/ 目录下
- 部署时直接复制，无需在线下载
- 各角色仅获取与其职责相关的skills

团队角色：
- video-director: 视频导演 | 主脑（监工）
- video-script-writer: 视频编剧
- remotion-core-dev: Remotion核心开发工程师
- remotion-media-dev: Remotion媒体特效工程师
- video-quality-analyst: 视频质量分析师
"""

import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .base import StudioTemplate, AgentConfig, load_template_agents


# Agents docs 基础目录
AGENTS_DOCS_DIR = Path(__file__).parent.parent.parent / "data" / "agents-docs" / "remotion_video"

# 角色到skills目录的映射
AGENT_SKILLS_ROLES = [
    "video-director",        # 主脑/监工
    "video-script-writer",   # 编剧
    "remotion-core-dev",     # 核心开发
    "remotion-media-dev",    # 媒体特效
    "video-quality-analyst", # 质量分析
]


class RemotionVideoTemplate(StudioTemplate):
    """Remotion视频工作室"""
    
    name = "Remotion视频工作室"
    description = "专业视频创作团队，包含视频导演（主脑/监工）、视频编剧、Remotion核心开发工程师、Remotion媒体特效工程师和视频质量分析师，专注于代码视频和创意视频内容制作"
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
    
    def deploy_skills_for_agent(self, agent_id: str, workspace: str) -> Tuple[bool, str]:
        """
        为指定Agent部署Remotion skills到其工作空间
        
        从 data/agents-docs/remotion_video/{agent_id}/skills/ 目录复制skills到工作空间
        
        Args:
            agent_id: Agent ID
            workspace: 工作空间路径
            
        Returns:
            (success, message)
        """
        if agent_id not in AGENT_SKILLS_ROLES:
            return False, f"未知的Agent ID: {agent_id}"
        
        source_dir = AGENTS_DOCS_DIR / agent_id / "skills"
        if not source_dir.exists():
            return False, f"Skills目录不存在: {source_dir}"
        
        workspace_path = Path(workspace).expanduser()
        skills_dir = workspace_path / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        
        copied_count = 0
        for skill_file in source_dir.glob("*.md"):
            dest = skills_dir / skill_file.name
            shutil.copy2(skill_file, dest)
            copied_count += 1
        
        return True, f"已部署 {copied_count} 个skill文件到 {skills_dir}"
    
    def deploy_all_skills(self, workspace_map: Dict[str, str]) -> Dict[str, Tuple[bool, str]]:
        """
        为所有Agent部署skills
        
        Args:
            workspace_map: Agent ID到工作空间的映射
            
        Returns:
            各Agent的部署结果
        """
        results = {}
        for agent_id, workspace in workspace_map.items():
            if agent_id in AGENT_SKILLS_ROLES:
                results[agent_id] = self.deploy_skills_for_agent(agent_id, workspace)
            else:
                results[agent_id] = (False, "该Agent不需要Remotion skills")
        return results
    
    def get_skills_summary(self) -> Dict[str, Any]:
        """
        获取Skills汇总信息
        
        Returns:
            Skills目录结构、各角色文件数等信息
        """
        summary = {
            "skills_base_dir": str(AGENTS_DOCS_DIR),
            "roles": {}
        }
        
        for role in AGENT_SKILLS_ROLES:
            role_dir = AGENTS_DOCS_DIR / role / "skills"
            if role_dir.exists():
                files = list(role_dir.glob("*.md"))
                summary["roles"][role] = {
                    "file_count": len(files),
                    "files": [f.name for f in files]
                }
            else:
                summary["roles"][role] = {"file_count": 0, "files": []}
        
        return summary
