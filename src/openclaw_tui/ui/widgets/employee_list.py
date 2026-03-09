"""员工列表组件"""
from textual.widgets import Static
from textual.containers import Grid
from textual.reactive import reactive

from .employee_card import EmployeeCard


class EmployeeList(Static):
    """员工列表 - 展示所有员工卡片"""
    
    employees = reactive(list)
    
    DEFAULT_CSS = """
    EmployeeList {
        width: 100%;
        height: 100%;
        content-align: center top;
    }
    EmployeeList Grid {
        grid-size: 3;
        grid-columns: 1fr 1fr 1fr;
        grid-rows: auto;
        grid-gutter: 0;
        width: 100%;
        height: auto;
    }
    """
    
    def __init__(self, employees: list = None, **kwargs):
        super().__init__(**kwargs)
        self.employees = employees or []
    
    def compose(self):
        """组装员工列表"""
        with Grid():
            for emp in self.employees:
                yield EmployeeCard(
                    employee_id=emp.get("id", ""),
                    name=emp.get("name", "Unknown"),
                    role=emp.get("role", ""),
                    avatar=emp.get("avatar", "👤"),
                    status=emp.get("status", "idle"),
                    current_task=emp.get("current_task", "")
                )
    
    def watch_employees(self, employees: list):
        """监听员工列表变化"""
        # 移除所有子组件并重新渲染
        for child in list(self.children):
            child.remove()
        
        with Grid():
            for emp in employees:
                self.mount(EmployeeCard(
                    employee_id=emp.get("id", ""),
                    name=emp.get("name", "Unknown"),
                    role=emp.get("role", ""),
                    avatar=emp.get("avatar", "👤"),
                    status=emp.get("status", "idle"),
                    current_task=emp.get("current_task", "")
                ))
    
    def update_employee_status(self, employee_id: str, status: str, task: str = ""):
        """更新指定员工的状态"""
        for card in self.query(EmployeeCard):
            if card.employee_id == employee_id:
                card.status = status
                if task:
                    card.current_task = task
                break
