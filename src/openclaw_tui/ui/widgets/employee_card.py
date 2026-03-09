"""员工卡片组件 - 支持鼠标和键盘双模式"""
from textual.widgets import Static
from textual.containers import Vertical
from textual.reactive import reactive
from textual import events


class EmployeeCard(Vertical):
    """员工卡片 - 扁平化设计，支持鼠标点击和键盘导航"""
    
    # 响应式属性
    name = reactive("")
    role = reactive("")
    status = reactive("idle")
    has_unread = reactive(False)
    current_task = reactive("")
    selected = reactive(False)
    hovered = reactive(False)
    
    DEFAULT_CSS = """
    EmployeeCard {
        width: 28;
        height: 12;
        background: $surface;
        border: solid $primary-darken-2;
        padding: 0;
        cursor: pointer;  /* 鼠标手型 */
    }
    EmployeeCard:hover {
        background: $surface-lighten-1;
        border: solid $primary;
    }
    EmployeeCard.hovered {
        background: $surface-lighten-1;
        border: solid $primary;
    }
    EmployeeCard:focus {
        border: solid $accent;
        background: $surface-lighten-2;
    }
    EmployeeCard.selected {
        border: solid $accent;
        background: $primary-darken-3;
    }
    EmployeeCard .card-header {
        height: 3;
        background: $primary-darken-3;
        content-align: center middle;
    }
    EmployeeCard:hover .card-header {
        background: $primary-darken-2;
    }
    EmployeeCard:focus .card-header {
        background: $accent-darken-1;
    }
    EmployeeCard.selected .card-header {
        background: $accent-darken-2;
    }
    EmployeeCard .card-body {
        height: 6;
        padding: 0 1;
        content-align: center middle;
    }
    EmployeeCard .card-footer {
        height: 3;
        content-align: center middle;
    }
    EmployeeCard .emoji-icon {
        text-style: bold;
        text-align: center;
    }
    EmployeeCard .name-text {
        text-style: bold;
        color: $text;
        text-align: center;
    }
    EmployeeCard .role-text {
        color: $text-muted;
        text-align: center;
    }
    EmployeeCard .status-indicator {
        text-align: center;
    }
    """
    
    def __init__(
        self,
        employee_id: str,
        name: str,
        role: str,
        status: str = "idle",
        has_unread: bool = False,
        current_task: str = "",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.employee_id = employee_id
        self.name = name
        self.role = role
        self.status = status
        self.has_unread = has_unread
        self.current_task = current_task
        self.can_focus = True  # 允许聚焦
    
    def compose(self):
        """组装卡片内容"""
        # 头部：状态指示器
        status_line = f"{self.status_emoji} {self.status_text}"
        if self.has_unread:
            status_line += "  💬"
        yield Static(status_line, classes="card-header status-indicator")
        
        # 主体：🦞 图标 + 姓名 + 角色
        with Vertical(classes="card-body"):
            yield Static("🦞", classes="emoji-icon")
            yield Static(self.name, classes="name-text")
            yield Static(self.role, classes="role-text")
        
        # 底部：当前任务
        task_display = self.current_task[:12] + "..." if len(self.current_task) > 12 else (self.current_task or "无任务")
        yield Static(f"📋 {task_display}", classes="card-footer")
    
    @property
    def status_emoji(self) -> str:
        return {"idle": "🟢", "working": "🟡", "offline": "⚫"}.get(self.status, "⚪")
    
    @property
    def status_text(self) -> str:
        return {"idle": "空闲", "working": "工作中", "offline": "离线"}.get(self.status, "未知")
    
    def watch_status(self, status: str):
        try:
            header = self.query_one(".card-header", Static)
            status_line = f"{self.status_emoji} {self.status_text}"
            if self.has_unread:
                status_line += "  💬"
            header.update(status_line)
        except Exception:
            pass
    
    def watch_has_unread(self, has_unread: bool):
        try:
            header = self.query_one(".card-header", Static)
            status_line = f"{self.status_emoji} {self.status_text}"
            if has_unread:
                status_line += "  💬"
            header.update(status_line)
        except Exception:
            pass
    
    def watch_current_task(self, task: str):
        try:
            footer = self.query_one(".card-footer", Static)
            display = task[:12] + "..." if len(task) > 12 else (task or "无任务")
            footer.update(f"📋 {display}")
        except Exception:
            pass
    
    def watch_selected(self, selected: bool):
        """监听选中状态"""
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")
    
    def watch_hovered(self, hovered: bool):
        """监听悬停状态"""
        if hovered:
            self.add_class("hovered")
        else:
            self.remove_class("hovered")
    
    # ========== 鼠标事件 ==========
    def on_enter(self, event: events.Enter) -> None:
        """鼠标进入卡片"""
        self.hovered = True
    
    def on_leave(self, event: events.Leave) -> None:
        """鼠标离开卡片"""
        self.hovered = False
    
    def on_click(self, event: events.Click) -> None:
        """鼠标点击卡片 - 进入对话"""
        self.app.push_screen("chat", {"employee_id": self.employee_id})
    
    # ========== 键盘事件 ==========
    def on_key(self, event):
        """处理键盘事件"""
        if event.key == "enter":
            # Enter 进入对话
            self.app.push_screen("chat", {"employee_id": self.employee_id})
            event.stop()
        elif event.key == "space":
            # 空格查看详情
            self.show_detail()
            event.stop()
    
    def show_detail(self):
        """显示员工详情"""
        self.app.notify(
            f"🦞 {self.name}\n"
            f"角色: {self.role}\n"
            f"状态: {self.status_text}\n"
            f"任务: {self.current_task or '无'}", 
            title="员工详情", 
            timeout=5
        )
