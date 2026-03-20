"""
Slidev PPT设计制作工作室模板
专业的PPT设计与制作团队，使用Slidev技术打造精美演示文稿

Skills说明：
- Skills预置在 data/agents-docs/slidev_ppt/{agent_id}/skills/ 目录下
- 部署时直接复制，无需在线下载
- 各角色仅获取与其职责相关的skills

团队角色（重新设计）：
- ppt-director: PPT项目总监 | 主脑（监工）
- ppt-content-architect: PPT内容架构师
- ppt-visual-designer: PPT视觉设计师
- ppt-code-specialist: PPT代码展示专家
- ppt-integrator: PPT集成工程师
- ppt-image-artist: 绘图大师（文生图）
"""

import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .base import StudioTemplate, AgentConfig, load_template_agents


# Agents docs 基础目录
AGENTS_DOCS_DIR = Path(__file__).parent.parent.parent / "data" / "agents-docs" / "slidev_ppt"

# 角色到skills目录的映射
AGENT_SKILLS_ROLES = [
    "ppt-director",           # 主脑/监工
    "ppt-content-architect",  # 内容架构师
    "ppt-visual-designer",    # 视觉设计师
    "ppt-code-specialist",    # 代码展示专家
    "ppt-integrator",         # 集成工程师
    "ppt-image-artist",       # 绘图大师
]


class SlidevPPTTemplate(StudioTemplate):
    """Slidev PPT设计制作工作室"""
    
    name = "PPT设计制作工作室"
    description = "专业的PPT设计与制作团队，包含PPT项目总监（主脑/监工）、内容架构师、视觉设计师、代码展示专家、集成工程师和绘图大师。使用Slidev技术打造精美、交互丰富的演示文稿。"
    default_architecture = "hybrid"
    
    def get_agents(self) -> List[AgentConfig]:
        """返回PPT制作团队的Agent配置"""
        return load_template_agents("slidev_ppt")
    
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
        为指定Agent部署Slidev skills到其工作空间
        
        从 data/agents-docs/slidev_ppt/{agent_id}/skills/ 目录复制skills到工作空间
        
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
                results[agent_id] = (False, "该Agent不需要Slidev skills")
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
