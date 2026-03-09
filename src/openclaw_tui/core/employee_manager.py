"""员工管理器"""
from typing import List, Optional, Callable
import asyncio

from ..openclaw.models import Employee, EmployeeStatus
from ..openclaw.client import OpenClawClient
from .state_manager import StateManager


class EmployeeManager:
    """员工管理器
    
    负责员工的生命周期管理，包括：
    - 加载员工列表
    - 更新员工状态
    - 处理员工相关事件
    """
    
    def __init__(self, client: OpenClawClient, state_manager: StateManager):
        self.client = client
        self.state = state_manager
        self._status_update_callbacks: List[Callable] = []
        self._polling_task: Optional[asyncio.Task] = None
        self._polling_interval = 30  # 轮询间隔（秒）
    
    async def load_employees(self) -> List[Employee]:
        """从 API 加载员工列表"""
        employees = await self.client.get_employees()
        for emp in employees:
            self.state.update_employee(emp)
        return employees
    
    async def refresh_employee(self, employee_id: str) -> Optional[Employee]:
        """刷新单个员工信息"""
        employee = await self.client.query_employee_status(employee_id)
        if employee:
            self.state.update_employee(employee)
        return employee
    
    def update_employee_status(self, employee_id: str, status: str, task: str = None):
        """更新员工状态"""
        self.state.update_employee_status(
            employee_id,
            EmployeeStatus(status),
            task
        )
        
        # 通知回调
        for callback in self._status_update_callbacks:
            try:
                callback(employee_id, status, task)
            except Exception as e:
                print(f"状态更新回调失败: {e}")
    
    def on_status_update(self, callback: Callable):
        """注册状态更新回调"""
        self._status_update_callbacks.append(callback)
    
    def start_polling(self):
        """启动状态轮询（作为 Webhook 的 fallback）"""
        if self._polling_task is None or self._polling_task.done():
            self._polling_task = asyncio.create_task(self._poll_loop())
    
    def stop_polling(self):
        """停止状态轮询"""
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
    
    async def _poll_loop(self):
        """轮询循环"""
        while True:
            try:
                await asyncio.sleep(self._polling_interval)
                employees = await self.client.get_employees()
                for emp in employees:
                    self.state.update_employee(emp)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"轮询失败: {e}")
    
    def get_employee(self, employee_id: str) -> Optional[Employee]:
        """获取员工信息"""
        return self.state.get_employee(employee_id)
    
    def get_all_employees(self) -> List[Employee]:
        """获取所有员工"""
        return self.state.get_employees_list()
    
    def get_online_count(self) -> int:
        """获取在线员工数量"""
        return sum(
            1 for emp in self.get_all_employees()
            if emp.status != EmployeeStatus.OFFLINE
        )
