"""数据模型定义"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class EmployeeStatus(Enum):
    """员工状态枚举"""
    IDLE = "idle"
    WORKING = "working"
    OFFLINE = "offline"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Employee:
    """员工模型"""
    id: str
    name: str
    role: str
    avatar: str = "👤"
    status: EmployeeStatus = EmployeeStatus.IDLE
    current_task: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "avatar": self.avatar,
            "status": self.status.value,
            "current_task": self.current_task,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Employee":
        """从字典创建"""
        return cls(
            id=data["id"],
            name=data["name"],
            role=data.get("role", ""),
            avatar=data.get("avatar", "👤"),
            status=EmployeeStatus(data.get("status", "idle")),
            current_task=data.get("current_task"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Task:
    """任务模型"""
    id: str
    employee_id: str
    content: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "content": self.content,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


@dataclass
class Message:
    """消息模型"""
    id: str
    employee_id: str
    content: str
    is_user: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "content": self.content,
            "is_user": self.is_user,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "task_id": self.task_id,
            "metadata": self.metadata,
        }
