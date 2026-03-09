"""员工数据模型 - 包含 OpenClaw 连接配置"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import json


class EmployeeStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class OpenClawConfig:
    """OpenClaw 连接配置"""
    base_url: str = ""           # 如: https://oc.example.com
    token: str = ""              # 认证 token
    session_key: str = "default" # 会话 key
    timeout: int = 120           # 超时时间(秒)
    enabled: bool = True         # 是否启用
    
    def to_dict(self) -> dict:
        return {
            "base_url": self.base_url,
            "token": self.token,
            "session_key": self.session_key,
            "timeout": self.timeout,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OpenClawConfig":
        return cls(
            base_url=data.get("base_url", ""),
            token=data.get("token", ""),
            session_key=data.get("session_key", "default"),
            timeout=data.get("timeout", 120),
            enabled=data.get("enabled", True),
        )


@dataclass
class Employee:
    """员工 - OpenClaw 员工"""
    id: str
    name: str
    role: str = "OpenClaw 员工"
    avatar: str = "🦞"
    status: EmployeeStatus = EmployeeStatus.OFFLINE
    current_task: Optional[str] = None
    last_active: Optional[datetime] = None
    unread_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # OpenClaw 连接配置
    config: OpenClawConfig = field(default_factory=OpenClawConfig)
    
    # 运行时状态（不序列化）
    connection_error: Optional[str] = field(default=None, repr=False)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "avatar": self.avatar,
            "status": self.status.value,
            "current_task": self.current_task,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "unread_count": self.unread_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "config": self.config.to_dict(),
            "connection_error": self.connection_error,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Employee":
        return cls(
            id=data["id"],
            name=data.get("name", "Unnamed"),
            role=data.get("role", "OpenClaw 员工"),
            avatar=data.get("avatar", "🦞"),
            status=EmployeeStatus(data.get("status", "offline")),
            current_task=data.get("current_task"),
            last_active=datetime.fromisoformat(data["last_active"]) if data.get("last_active") else None,
            unread_count=data.get("unread_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            config=OpenClawConfig.from_dict(data.get("config", {})),
            connection_error=data.get("connection_error"),
        )
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.updated_at = datetime.now()


# 内存存储
class EmployeeStore:
    """员工数据存储"""
    
    def __init__(self):
        self._employees: Dict[str, Employee] = {}
        self._messages: Dict[str, List[dict]] = {}
        self._load_default()
    
    def _load_default(self):
        """加载默认员工（演示用）"""
        defaults = [
            Employee(
                id="emp-001",
                name="Alice",
                role="代码审查专家",
                config=OpenClawConfig(
                    base_url="wss://gateway.openclaw.example.com",
                    token="oc_token_alice",
                    session_key="alice-session",
                )
            ),
            Employee(
                id="emp-002",
                name="Bob",
                role="文档生成助手",
                config=OpenClawConfig(
                    base_url="wss://gateway.openclaw.example.com",
                    token="oc_token_bob",
                    session_key="bob-session",
                )
            ),
        ]
        for emp in defaults:
            self._employees[emp.id] = emp
            self._messages[emp.id] = []
    
    # CRUD 操作
    def create(self, employee: Employee) -> Employee:
        """创建员工"""
        if employee.id in self._employees:
            raise ValueError(f"员工 ID 已存在: {employee.id}")
        self._employees[employee.id] = employee
        self._messages[employee.id] = []
        return employee
    
    def get(self, employee_id: str) -> Optional[Employee]:
        """获取员工"""
        return self._employees.get(employee_id)
    
    def get_all(self) -> List[Employee]:
        """获取所有员工"""
        return list(self._employees.values())
    
    def update(self, employee_id: str, **kwargs) -> Optional[Employee]:
        """更新员工"""
        emp = self._employees.get(employee_id)
        if not emp:
            return None
        
        for key, value in kwargs.items():
            if key == "config" and isinstance(value, dict):
                emp.config = OpenClawConfig.from_dict(value)
            elif hasattr(emp, key) and key != "id":
                setattr(emp, key, value)
        
        emp.updated_at = datetime.now()
        return emp
    
    def delete(self, employee_id: str) -> bool:
        """删除员工"""
        if employee_id in self._employees:
            del self._employees[employee_id]
            del self._messages[employee_id]
            return True
        return False
    
    def update_status(self, employee_id: str, status: str, task: str = None, error: str = None):
        """更新员工状态"""
        emp = self._employees.get(employee_id)
        if emp:
            emp.status = EmployeeStatus(status)
            if task is not None:
                emp.current_task = task
            if error is not None:
                emp.connection_error = error
            emp.last_active = datetime.now()
    
    # 消息管理
    def add_message(self, employee_id: str, content: str, is_user: bool = False) -> dict:
        """添加消息"""
        if employee_id not in self._messages:
            self._messages[employee_id] = []
        
        msg = {
            "id": f"msg-{datetime.now().timestamp()}",
            "employee_id": employee_id,
            "content": content,
            "is_user": is_user,
            "timestamp": datetime.now().isoformat(),
        }
        self._messages[employee_id].append(msg)
        
        if not is_user:
            emp = self._employees.get(employee_id)
            if emp:
                emp.unread_count += 1
        
        return msg
    
    def get_messages(self, employee_id: str) -> List[dict]:
        """获取消息"""
        return self._messages.get(employee_id, [])
    
    def clear_unread(self, employee_id: str):
        """清除未读"""
        emp = self._employees.get(employee_id)
        if emp:
            emp.unread_count = 0


# 全局实例
employee_store = EmployeeStore()
