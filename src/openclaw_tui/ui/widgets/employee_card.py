"""员工卡片组件 - 平面设计风格"""
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel


class EmployeeCard(Vertical):
    """员工卡片 - 扁平化设计，使用emoji图标"""
    
    # 响应式属性
    name = reactive("")
    role = reactive("")
    status = reactive("idle")  # idle, working, offline
    has_unread = reactive(False)
    current_task = reactive("")
    
    DEFAULT_CSS = """
    EmployeeCard {
        width: 28;
        height: 12;
        background: $surface;
        border: solid $primary-darken-2;
        padding: 0;
    }
    EmployeeCard:hover {
        background: $surface-lighten-1;
        border: solid $primary;
    }
    EmployeeCard .card-header {
        height: 3;
        background: $primary-darken-3;
        content-align: center middle;
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
    }
    EmployeeCard .name-text {
        text-style: bold;
        color: $text;
    }
    EmployeeCard .role-text {
        color: $text-muted;
    }
    EmployeeCard .status-indicator {
        text-align: center;
    }
    EmployeeCard .unread-badge {
        color: $warning;
        text-style: bold;
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
    
    def compose(self):
        """组装卡片内容 - 三部分：头部、内容、底部"""
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
        
        # 底部：当前任务 + 操作按钮
        task_display = self.current_task[:12] + "..." if len(self.current_task) > 12 else (self.current_task or "无任务")
        yield Static(f"📋 {task_display}", classes="card-footer")
    
    @property
    def status_emoji(self) -> str:
        """状态对应的emoji"""
        return {
            "idle": "🟢",
            "working": "🟡",
            "offline": "⚫",
        }.get(self.status, "⚪")
    
    @property
    def status_text(self) -> str:
        """状态文本"""
        return {
            "idle": "空闲",
            "working": "工作中",
            "offline": "离线",
        }.get(self.status, "未知")
    
    def watch_status(self, status: str):
        """监听状态变化"""
        try:
            header = self.query_one(".card-header", Static)
            status_line = f"{self.status_emoji} {self.status_text}"
            if self.has_unread:
                status_line += "  💬"
            header.update(status_line)
        except Exception:
            pass
    
    def watch_has_unread(self, has_unread: bool):
        """监听未读消息变化"""
        try:
            header = self.query_one(".card-header", Static)
            status_line = f"{self.status_emoji} {self.status_text}"
            if has_unread:
                status_line += "  💬"
            header.update(status_line)
        except Exception:
            pass
    
    def watch_current_task(self, task: str):
        """监听任务变化"""
        try:
            footer = self.query_one(".card-footer", Static)
            display = task[:12] + "..." if len(task) > 12 else (task or "无任务")
            footer.update(f"📋 {display}")
        except Exception:
            pass
    
    def on_click(self):
        """点击卡片进入对话"""
        self.app.push_screen("chat", {"employee_id": self.employee_id})
