"""
数据模型 - 员工和存储
支持多智能体架构（混合模式）
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, List, Any


@dataclass
class Employee:
    """开放智能体员工 - 映射到 OpenClaw Agent"""
    id: str
    name: str  # 英文全名，如 "Alex Chen"
    role: str = "OpenClaw 员工"
    status: str = "offline"  # offline, idle, working, error
    current_task: str = ""
    unread_count: int = 0
    enabled: bool = True
    last_error: str = ""
    config: Dict = field(default_factory=dict)
    
    # 多智能体配置
    agent_id: str = ""           # OpenClaw agent ID (如: product-manager, programmer)
    display_name: str = ""       # 显示名称（如: Alex）
    workspace: str = ""          # 工作区路径
    agent_dir: str = ""          # agent状态目录
    session_key: str = ""        # 会话键 (格式: agent:<agentId>:<mainKey>)
    model: str = "volcengine/glm-4.7"  # 模型配置
    is_main_brain: bool = False  # 是否为主脑
    agent_type: str = "specialist"  # main_brain, specialist
    
    # 身份和性格配置
    emoji: str = "🍄"            # 角色emoji标识
    personality: str = ""        # 性格描述
    specialty: str = ""          # 专长/任务描述
    
    # 工具权限配置
    allowed_tools: List[str] = field(default_factory=list)
    denied_tools: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果 agent_id 为空，默认使用 employee id
        if not self.agent_id:
            self.agent_id = self.id
        
        # 如果 display_name 为空，使用 name
        if not self.display_name:
            self.display_name = self.name.split()[0] if self.name else self.id
        
        # 如果 session_key 为空，生成默认会话键
        if not self.session_key:
            self.session_key = f"agent:{self.agent_id}:main"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Employee":
        """从字典创建"""
        # 过滤掉不存在的字段
        valid_fields = {k for k in cls.__dataclass_fields__.keys()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


@dataclass
class MultiAgentConfig:
    """多智能体全局配置"""
    enabled: bool = True
    mode: str = "hybrid"  # hybrid, single
    agent_to_agent_enabled: bool = True
    allowed_agents: List[str] = field(default_factory=list)
    dm_scope: str = "main"  # main, per-peer, per-channel-peer
    base_workspace: str = "~/.openclaw/MushTech"
    default_model: str = "volcengine/glm-4.7"
    
    # 团队预设配置
    main_brain: Dict = field(default_factory=dict)
    specialists: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "MultiAgentConfig":
        valid_fields = {k for k in cls.__dataclass_fields__.keys()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


class EmployeeStore:
    """员工数据管理 - 支持多智能体"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_file = self.data_dir / "employees.json"
        self.config_file = self.data_dir / "multi_agent_config.json"
        self.data_dir.mkdir(exist_ok=True)
        
        self.employees: Dict[str, Employee] = {}
        self.multi_agent_config = MultiAgentConfig()
        
        # 加载studio配置
        self._load_studio_config()
        
        self.load()
    
    def _load_studio_config(self):
        """从studio_config加载Gateway配置"""
        try:
            from .config_manager import get_config_manager
            studio_config = get_config_manager().get_config()
            
            # 更新multi_agent_config
            self.multi_agent_config.mode = studio_config.architecture
            self.multi_agent_config.base_workspace = studio_config.base_workspace
        except Exception as e:
            print(f"加载Studio配置失败: {e}")
    
    def load(self):
        """加载员工数据"""
        # 加载员工数据
        if self.data_file.exists():
            try:
                data = json.loads(self.data_file.read_text(encoding='utf-8'))
                # 跳过配置数据，只加载员工
                for emp_id, emp_data in data.items():
                    if not emp_id.startswith("_"):
                        self.employees[emp_id] = Employee.from_dict(emp_data)
            except Exception as e:
                print(f"加载员工数据失败: {e}")
        
        # 加载多智能体配置
        if self.config_file.exists():
            try:
                config_data = json.loads(self.config_file.read_text(encoding='utf-8'))
                self.multi_agent_config = MultiAgentConfig.from_dict(config_data)
            except Exception as e:
                print(f"加载多智能体配置失败: {e}")
        
        # 如果没有员工，创建默认团队
        if not self.employees:
            self.create_default_team()
    
    def save(self):
        """保存员工数据"""
        # 保存员工数据
        data = {}
        for emp_id, emp in self.employees.items():
            data[emp_id] = emp.to_dict()
        
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), 
                encoding='utf-8'
            )
        except Exception as e:
            print(f"保存员工数据失败: {e}")
        
        # 保存多智能体配置
        try:
            self.config_file.write_text(
                json.dumps(self.multi_agent_config.to_dict(), indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            print(f"保存多智能体配置失败: {e}")
    
    def create_default_team(self):
        """创建默认 MushTech 团队 - 使用模板系统"""
        try:
            from .config_manager import get_config_manager
            from .templates import get_template
            
            studio_config = get_config_manager().get_config()
            base_workspace = studio_config.base_workspace
            
            # 使用当前工作室类型的模板
            template = get_template(studio_config.studio_type)
            
            # 获取员工配置
            employees_data = template.get_employees_config(
                base_workspace,
                studio_config.architecture,
            )
            
            # 创建员工对象
            for emp_data in employees_data:
                emp_id = emp_data["id"]
                emp = Employee.from_dict(emp_data)
                self.employees[emp_id] = emp
            
            # 更新团队配置
            agents = template.get_agents()
            main_brain = None
            specialists = []
            
            for agent in agents:
                agent_dict = agent.to_dict()
                if agent.is_main_brain:
                    main_brain = agent_dict
                else:
                    specialists.append(agent_dict)
            
            self.multi_agent_config.main_brain = main_brain or {}
            self.multi_agent_config.specialists = specialists
            self.multi_agent_config.allowed_agents = [a.id for a in agents]
            self.multi_agent_config.mode = studio_config.architecture
            self.multi_agent_config.base_workspace = base_workspace
            
            self.save()
            
        except Exception as e:
            print(f"创建默认团队失败: {e}")
            # 如果失败，创建一个空团队
            self.employees = {}
            self.save()
    
    def add(self, emp: Employee):
        """添加员工"""
        self.employees[emp.id] = emp
        self.save()
    
    def delete(self, emp_id: str):
        """删除员工"""
        if emp_id in self.employees:
            del self.employees[emp_id]
            self.save()
    
    def update(self, emp_id: str, **kwargs):
        """更新员工"""
        if emp_id in self.employees:
            emp = self.employees[emp_id]
            for key, value in kwargs.items():
                if hasattr(emp, key):
                    setattr(emp, key, value)
            self.save()
    

    
    def update_multi_agent_config(self, **kwargs):
        """更新多智能体配置"""
        for key, value in kwargs.items():
            if hasattr(self.multi_agent_config, key):
                setattr(self.multi_agent_config, key, value)
        self.save()
    

# 工具函数
def create_employee_from_agent_config(
    agent_id: str,
    name: str,
    role: str,
    workspace: str,
    model: str = "volcengine/glm-4.7",
    is_main_brain: bool = False,
    allowed_tools: Optional[List[str]] = None,
    emoji: str = "🍄",
    personality: str = "",
    specialty: str = ""
) -> Employee:
    """从 Agent 配置创建员工"""
    
    emp_id = f"emp-{agent_id.replace('_', '-')}"
    agent_dir = f"~/.openclaw/agents/{agent_id}/agent"
    session_key = f"agent:{agent_id}:main"
    display_name = name.split()[0] if " " in name else name
    
    return Employee(
        id=emp_id,
        name=name,
        display_name=display_name,
        role=role,
        agent_id=agent_id,
        agent_type="main_brain" if is_main_brain else "specialist",
        is_main_brain=is_main_brain,
        workspace=workspace,
        agent_dir=agent_dir,
        session_key=session_key,
        model=model,
        allowed_tools=allowed_tools or [],
        emoji=emoji,
        personality=personality,
        specialty=specialty
    )
