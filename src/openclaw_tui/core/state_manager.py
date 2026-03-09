"""状态管理器 - 响应式状态管理"""
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import asyncio
from datetime import datetime

from ..openclaw.models import Employee, Task, Message, EmployeeStatus, TaskStatus


@dataclass
class AppState:
    """应用状态"""
    employees: Dict[str, Employee] = field(default_factory=dict)
    tasks: Dict[str, Task] = field(default_factory=dict)
    messages: Dict[str, List[Message]] = field(default_factory=dict)
    connected: bool = False
    current_employee_id: Optional[str] = None


class StateManager:
    """状态管理器
    
    管理应用的响应式状态，提供订阅机制让 UI 组件自动更新。
    """
    
    def __init__(self):
        self._state = AppState()
        self._subscribers: Dict[str, List[Callable]] = {
            "employees": [],
            "tasks": [],
            "messages": [],
            "connection": [],
        }
        self._lock = asyncio.Lock()
    
    # 订阅机制
    def subscribe(self, event_type: str, callback: Callable):
        """订阅状态变化"""
        if event_type in self._subscribers:
            self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)
    
    def _notify(self, event_type: str, data: Any = None):
        """通知订阅者"""
        for callback in self._subscribers.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                print(f"通知订阅者失败: {e}")
    
    # 员工管理
    def update_employee(self, employee: Employee):
        """更新员工信息"""
        self._state.employees[employee.id] = employee
        self._notify("employees", self.get_employees_list())
    
    def update_employee_status(self, employee_id: str, status: EmployeeStatus, task: str = None):
        """更新员工状态"""
        if employee_id in self._state.employees:
            emp = self._state.employees[employee_id]
            emp.status = status
            if task is not None:
                emp.current_task = task
            emp.last_active = datetime.now()
            self._notify("employees", self.get_employees_list())
    
    def get_employee(self, employee_id: str) -> Optional[Employee]:
        """获取员工信息"""
        return self._state.employees.get(employee_id)
    
    def get_employees_list(self) -> List[Employee]:
        """获取所有员工列表"""
        return list(self._state.employees.values())
    
    # 任务管理
    def add_task(self, task: Task):
        """添加任务"""
        self._state.tasks[task.id] = task
        self._notify("tasks", task)
    
    def update_task_status(self, task_id: str, status: TaskStatus, result: str = None, error: str = None):
        """更新任务状态"""
        if task_id in self._state.tasks:
            task = self._state.tasks[task_id]
            task.status = status
            if result:
                task.result = result
            if error:
                task.error = error
            if status == TaskStatus.RUNNING:
                task.started_at = datetime.now()
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                task.completed_at = datetime.now()
            self._notify("tasks", task)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务信息"""
        return self._state.tasks.get(task_id)
    
    def get_employee_tasks(self, employee_id: str) -> List[Task]:
        """获取员工的任务列表"""
        return [t for t in self._state.tasks.values() if t.employee_id == employee_id]
    
    # 消息管理
    def add_message(self, message: Message):
        """添加消息"""
        if message.employee_id not in self._state.messages:
            self._state.messages[message.employee_id] = []
        self._state.messages[message.employee_id].append(message)
        self._notify("messages", message)
    
    def get_messages(self, employee_id: str) -> List[Message]:
        """获取与某员工的消息历史"""
        return self._state.messages.get(employee_id, [])
    
    # 连接状态
    @property
    def connected(self) -> bool:
        return self._state.connected
    
    @connected.setter
    def connected(self, value: bool):
        self._state.connected = value
        self._notify("connection", value)
    
    # 当前选中员工
    @property
    def current_employee_id(self) -> Optional[str]:
        return self._state.current_employee_id
    
    @current_employee_id.setter
    def current_employee_id(self, value: Optional[str]):
        self._state.current_employee_id = value
