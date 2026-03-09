"""数据模型"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import json


class EmployeeStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    OFFLINE = "offline"


@dataclass
class Employee:
    id: str
    name: str
    role: str
    status: EmployeeStatus = EmployeeStatus.IDLE
    current_task: Optional[str] = None
    avatar: str = "🦞"
    last_active: Optional[datetime] = None
    unread_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "current_task": self.current_task,
            "avatar": self.avatar,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "unread_count": self.unread_count,
        }


@dataclass
class Message:
    id: str
    employee_id: str
    content: str
    is_user: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "content": self.content,
            "is_user": self.is_user,
            "timestamp": self.timestamp.isoformat(),
        }


# 内存存储（生产环境可改为数据库）
class DataStore:
    """数据存储"""
    
    def __init__(self):
        self.employees: Dict[str, Employee] = {}
        self.messages: Dict[str, List[Message]] = {}
        self._init_default_data()
    
    def _init_default_data(self):
        """初始化默认员工数据"""
        default_employees = [
            Employee("alice-001", "Alice", "代码审查专家", EmployeeStatus.IDLE),
            Employee("bob-002", "Bob", "文档生成助手", EmployeeStatus.WORKING, "生成 API 文档"),
            Employee("carol-003", "Carol", "测试工程师", EmployeeStatus.IDLE),
            Employee("dave-004", "Dave", "DevOps 专家", EmployeeStatus.OFFLINE),
            Employee("eve-005", "Eve", "数据分析助手", EmployeeStatus.WORKING, "分析日志数据"),
        ]
        for emp in default_employees:
            self.employees[emp.id] = emp
            self.messages[emp.id] = []
        
        # 添加一些测试消息
        self.messages["bob-002"] = [
            Message("msg-1", "bob-002", "文档生成完成 50%", False),
            Message("msg-2", "bob-002", "继续生成中...", False),
        ]
        self.employees["bob-002"].unread_count = 2
        
        self.messages["eve-005"] = [
            Message("msg-3", "eve-005", "发现异常数据模式", False),
        ]
        self.employees["eve-005"].unread_count = 1
    
    def get_employees(self) -> List[Employee]:
        return list(self.employees.values())
    
    def get_employee(self, employee_id: str) -> Optional[Employee]:
        return self.employees.get(employee_id)
    
    def update_employee_status(self, employee_id: str, status: str, task: str = None):
        if employee_id in self.employees:
            self.employees[employee_id].status = EmployeeStatus(status)
            if task is not None:
                self.employees[employee_id].current_task = task
            self.employees[employee_id].last_active = datetime.now()
    
    def add_message(self, employee_id: str, content: str, is_user: bool = False) -> Message:
        msg = Message(
            id=f"msg-{datetime.now().timestamp()}",
            employee_id=employee_id,
            content=content,
            is_user=is_user
        )
        if employee_id not in self.messages:
            self.messages[employee_id] = []
        self.messages[employee_id].append(msg)
        
        if not is_user:
            self.employees[employee_id].unread_count += 1
        
        return msg
    
    def get_messages(self, employee_id: str) -> List[Message]:
        return self.messages.get(employee_id, [])
    
    def clear_unread(self, employee_id: str):
        if employee_id in self.employees:
            self.employees[employee_id].unread_count = 0


# 全局数据存储实例
store = DataStore()
