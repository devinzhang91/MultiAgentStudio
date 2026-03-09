"""员工列表组件 - 平面网格布局"""
from textual.widgets import Static
from textual.containers import Grid
from textual.reactive import reactive

from .employee_card import EmployeeCard


class EmployeeList(Static):
    """员工列表 - 平面网格布局展示所有员工"""
    
    employees = reactive(list)
    unread_counts = reactive(dict)  # {employee_id: count}
    
    DEFAULT_CSS = """
    EmployeeList {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    EmployeeList Grid {
        grid-size: 4;
        grid-columns: 1fr 1fr 1fr 1fr;
        grid-rows: auto;
        grid-gutter: 1;
        width: 100%;
        height: auto;
    }
    """
    
    def __init__(self, employees: list = None, **kwargs):
        super().__init__(**kwargs)
        self.employees = employees or []
        self.unread_counts = {}
    
    def compose(self):
        """组装员工列表"""
        with Grid():
            for emp in self.employees:
                unread = self.unread_counts.get(emp.get("id"), 0) > 0
                yield EmployeeCard(
                    employee_id=emp.get("id", ""),
                    name=emp.get("name", "Unknown"),
                    role=emp.get("role", ""),
                    status=emp.get("status", "idle"),
                    has_unread=unread,
                    current_task=emp.get("current_task", "")
                )
    
    def watch_employees(self, employees: list):
        """监听员工列表变化"""
        grid = self.query_one(Grid)
        grid.remove_children()
        
        for emp in employees:
            unread = self.unread_counts.get(emp.get("id"), 0) > 0
            grid.mount(EmployeeCard(
                employee_id=emp.get("id", ""),
                name=emp.get("name", "Unknown"),
                role=emp.get("role", ""),
                status=emp.get("status", "idle"),
                has_unread=unread,
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
    
    def set_unread(self, employee_id: str, count: int):
        """设置员工的未读消息数"""
        self.unread_counts[employee_id] = count
        for card in self.query(EmployeeCard):
            if card.employee_id == employee_id:
                card.has_unread = count > 0
                break
