"""员工列表组件 - 支持键盘导航"""
from textual.widgets import Static
from textual.containers import Grid
from textual.reactive import reactive

from .employee_card import EmployeeCard


class EmployeeList(Static):
    """员工列表 - 网格布局，支持方向键导航"""
    
    employees = reactive(list)
    unread_counts = reactive(dict)
    selected_index = reactive(0)  # 当前选中索引
    
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
    EmployeeList .nav-hint {
        height: 1;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
        margin-top: 1;
    }
    """
    
    def __init__(self, employees: list = None, **kwargs):
        super().__init__(**kwargs)
        self.employees = employees or []
        self.unread_counts = {}
        self._cards = []  # 缓存卡片引用
    
    def compose(self):
        """组装员工列表"""
        with Grid():
            for i, emp in enumerate(self.employees):
                unread = self.unread_counts.get(emp.get("id"), 0) > 0
                card = EmployeeCard(
                    employee_id=emp.get("id", ""),
                    name=emp.get("name", "Unknown"),
                    role=emp.get("role", ""),
                    status=emp.get("status", "idle"),
                    has_unread=unread,
                    current_task=emp.get("current_task", "")
                )
                card.selected = (i == self.selected_index)
                self._cards.append(card)
                yield card
        
        yield Static("↑/↓/←/→ 导航 │ Enter 对话 │ Space 详情 │ q 退出", classes="nav-hint")
    
    def on_mount(self):
        """挂载后聚焦第一个卡片"""
        if self._cards:
            self._cards[0].focus()
    
    def watch_employees(self, employees: list):
        """监听员工列表变化"""
        grid = self.query_one(Grid)
        grid.remove_children()
        self._cards = []
        
        for i, emp in enumerate(employees):
            unread = self.unread_counts.get(emp.get("id"), 0) > 0
            card = EmployeeCard(
                employee_id=emp.get("id", ""),
                name=emp.get("name", "Unknown"),
                role=emp.get("role", ""),
                status=emp.get("status", "idle"),
                has_unread=unread,
                current_task=emp.get("current_task", "")
            )
            card.selected = (i == self.selected_index)
            self._cards.append(card)
            grid.mount(card)
        
        # 重新聚焦
        if self._cards and self.selected_index < len(self._cards):
            self._cards[self.selected_index].focus()
    
    def on_key(self, event):
        """处理方向键导航"""
        if not self._cards:
            return
        
        cols = 4  # 网格列数
        rows = (len(self._cards) + cols - 1) // cols
        current = self.selected_index
        new_index = current
        
        if event.key == "up":
            new_index = current - cols
            event.stop()
        elif event.key == "down":
            new_index = current + cols
            event.stop()
        elif event.key == "left":
            new_index = current - 1
            event.stop()
        elif event.key == "right":
            new_index = current + 1
            event.stop()
        elif event.key == "home":
            new_index = 0
            event.stop()
        elif event.key == "end":
            new_index = len(self._cards) - 1
            event.stop()
        
        # 边界检查
        if new_index != current and 0 <= new_index < len(self._cards):
            # 更新选中状态
            self._cards[current].selected = False
            self._cards[new_index].selected = True
            self._cards[new_index].focus()
            self.selected_index = new_index
    
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
