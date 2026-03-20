"""
工作室模板基类
定义工作室模板的接口和规范
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    """Agent配置数据类"""
    id: str
    employee_id: str
    name: str
    display_name: str
    role: str
    agent_type: str  # "main_brain" | "specialist" | "coordinator"
    is_main_brain: bool
    emoji: str
    avatar: str
    personality: str
    specialty: str
    allowed_tools: List[str]
    denied_tools: List[str]
    model: str = "volcengine/glm-4.7"
    bootstrap_docs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "role": self.role,
            "agent_type": self.agent_type,
            "is_main_brain": self.is_main_brain,
            "emoji": self.emoji,
            "avatar": self.avatar,
            "personality": self.personality,
            "specialty": self.specialty,
            "allowed_tools": self.allowed_tools,
            "denied_tools": self.denied_tools,
            "model": self.model,
        }


class StudioTemplate(ABC):
    """工作室模板基类"""
    
    # 模板元数据
    name: str = ""
    description: str = ""
    default_architecture: str = "hybrid"  # centralized | decentralized | hybrid
    
    @abstractmethod
    def get_agents(self) -> List[AgentConfig]:
        """
        返回Agent配置列表
        
        Returns:
            List[AgentConfig]: Agent配置列表
        """
        pass
    
    @abstractmethod
    def get_agent_to_agent_config(self) -> Dict[str, Any]:
        """
        返回agentToAgent配置
        
        Returns:
            Dict: agentToAgent配置
        """
        pass

    def get_primary_agent(self) -> AgentConfig:
        """返回主脑角色；若模板未显式声明，则取首位成员"""
        agents = self.get_agents()
        for agent in agents:
            if agent.is_main_brain:
                return agent
        return agents[0]

    def get_workspace_map(self, base_workspace: str, architecture: str) -> Dict[str, str]:
        """根据架构生成每个Agent的工作空间布局"""
        primary_agent = self.get_primary_agent()
        shared_workspace = f"{base_workspace}/workspace/team-shared"

        workspace_map: Dict[str, str] = {}
        for agent in self.get_agents():
            if architecture == "decentralized":
                workspace_map[agent.id] = shared_workspace
            elif architecture == "hybrid":
                if agent.id == primary_agent.id:
                    workspace_map[agent.id] = f"{base_workspace}/workspace/{agent.id}"
                else:
                    workspace_map[agent.id] = shared_workspace
            else:
                workspace_map[agent.id] = f"{base_workspace}/workspace/{agent.id}"

        return workspace_map
    
    def get_openclaw_agents_config(self, base_workspace: str, architecture: str) -> List[Dict[str, Any]]:
        """
        生成OpenClaw格式的agents配置
        
        注意：只包含OpenClaw识别的字段，移除不被识别的字段：
        - subagents (maxConcurrent, allowlist)
        - agentToAgent
        
        Args:
            base_workspace: 基础工作空间路径
            
        Returns:
            List[Dict]: OpenClaw格式的agents列表
        """
        agents = []
        workspace_map = self.get_workspace_map(base_workspace, architecture)
        for agent in self.get_agents():
            workspace = workspace_map[agent.id]
            
            # 构建agent配置（只包含OpenClaw识别的字段）
            agent_config = {
                "id": agent.id,
                "name": agent.id,
                "workspace": workspace,
                "agentDir": f"~/.openclaw/agents/{agent.id}/agent",
                "identity": {
                    "name": agent.name,
                    "emoji": agent.emoji
                }
            }
            
            # 注意：OpenClaw不识别以下字段，已移除
            # - subagents (包含maxConcurrent, allowlist)
            # - agentToAgent
            
            agents.append(agent_config)
        
        return agents
    
    def get_employees_config(self, base_workspace: str, architecture: str) -> List[Dict[str, Any]]:
        """
        生成MushTech Studio格式的employees配置
        
        Args:
            base_workspace: 基础工作空间路径
            
        Returns:
            List[Dict]: employees配置列表
        """
        employees = []
        workspace_map = self.get_workspace_map(base_workspace, architecture)
        for agent in self.get_agents():
            emp_id = agent.employee_id or f"emp-{agent.id.replace('_', '-')}"
            workspace = workspace_map[agent.id]
            
            employee = {
                "id": emp_id,
                "name": agent.name,
                "display_name": agent.display_name,
                "role": agent.role,
                "agent_id": agent.id,
                "agent_type": agent.agent_type,
                "is_main_brain": agent.is_main_brain,
                "emoji": agent.emoji or agent.avatar,
                "workspace": workspace,
                "agent_dir": f"~/.openclaw/agents/{agent.id}/agent",
                "session_key": f"agent:{agent.id}:main",
                "model": agent.model,
                "personality": agent.personality,
                "specialty": agent.specialty,
                "allowed_tools": agent.allowed_tools,
                "denied_tools": agent.denied_tools,
                "config": {"session_key": f"agent:{agent.id}:main"},
                "status": "offline",
                "current_task": "",
                "unread_count": 0,
                "enabled": True,
                "last_error": "",
            }
            employees.append(employee)
        
        return employees
    
    def get_full_openclaw_config(self, base_workspace: str, architecture: str) -> Dict[str, Any]:
        """
        生成完整的OpenClaw配置片段
        
        注意：只包含OpenClaw识别的字段
        
        Args:
            base_workspace: 基础工作空间路径
            
        Returns:
            Dict: 包含agents.list的配置
        """
        return {
            "agents": {
                "list": self.get_openclaw_agents_config(base_workspace, architecture)
            }
        }


# 模板类映射（延迟导入以避免循环依赖）
_TEMPLATE_REGISTRY = {
    "software_engineering": (".software_engineering", "SoftwareEngineeringTemplate"),
    "remotion_video": (".remotion_video", "RemotionVideoTemplate"),
    "stock_analysis": (".stock_analysis", "StockAnalysisTemplate"),
    "slidev_ppt": (".slidev_ppt", "SlidevPPTTemplate"),
}


def _get_template_class(studio_type: str):
    """根据类型获取模板类（内部辅助函数）"""
    import importlib
    
    module_path, class_name = _TEMPLATE_REGISTRY.get(
        studio_type, 
        _TEMPLATE_REGISTRY["software_engineering"]
    )
    module = importlib.import_module(module_path, __package__)
    return getattr(module, class_name)


def get_template(studio_type: str) -> StudioTemplate:
    """
    根据类型获取模板实例
    
    Args:
        studio_type: 工作室类型
        
    Returns:
        StudioTemplate: 模板实例
    """
    template_class = _get_template_class(studio_type)
    return template_class()


def list_templates() -> List[Dict[str, str]]:
    """
    列出所有可用模板
    
    Returns:
        List[Dict]: 模板信息列表
    """
    templates = []
    for studio_type in _TEMPLATE_REGISTRY.keys():
        template_class = _get_template_class(studio_type)
        templates.append({
            "id": studio_type,
            "name": template_class.name,
            "description": template_class.description,
            "default_architecture": template_class.default_architecture,
        })
    return templates


def load_template_agents(template_id: str) -> List[AgentConfig]:
    """从 prompts JSON 加载模板 agents 与初始化文档配置"""
    prompts_dir = Path(__file__).parent / "prompts"
    agents_path = prompts_dir / f"{template_id}.json"
    docs_path = prompts_dir / f"{template_id}_docs.json"

    agents_data = json.loads(agents_path.read_text(encoding="utf-8"))
    docs_data: Dict[str, Any] = {}
    if docs_path.exists():
        docs_data = json.loads(docs_path.read_text(encoding="utf-8"))

    agents: List[AgentConfig] = []
    for entry in agents_data:
        agents.append(
            AgentConfig(
                id=entry.get("id"),
                employee_id=entry.get("employee_id"),
                name=entry.get("name"),
                display_name=entry.get("display_name"),
                role=entry.get("role"),
                agent_type=entry.get("agent_type"),
                is_main_brain=bool(entry.get("is_main_brain")),
                emoji=entry.get("emoji") or "",
                avatar=entry.get("avatar") or "",
                personality=entry.get("personality") or "",
                specialty=entry.get("specialty") or "",
                allowed_tools=entry.get("allowed_tools") or [],
                denied_tools=entry.get("denied_tools") or [],
                model=entry.get("model") or "volcengine/glm-4.7",
                bootstrap_docs=docs_data.get(entry.get("id"), {}),
            )
        )

    return agents
