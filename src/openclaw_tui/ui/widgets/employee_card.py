"""员工卡片组件"""
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive


class EmployeeCard(Vertical):
    """员工卡片 - 展示单个员工的信息和状态"""
    
    # 响应式属性
    name = reactive("")
    role = reactive("")
    status = reactive("idle")  # idle, working, offline
    avatar = reactive("👤")
    current_task = reactive("")
    
    DEFAULT_CSS = """
    EmployeeCard {
        width: 24;
        height: auto;
        border: solid $primary;
        background: $surface-darken-1;
        padding: 1;
        margin: 1;
    }
    EmployeeCard:hover {
        background: $surface-darken-2;
    }
    EmployeeCard .avatar {
        text-style: bold;
        text-align: center;
        width: 100%;
    }
    EmployeeCard .name {
        text-style: bold;
        text-align: center;
        color: $text;
    }
    EmployeeCard .role {
        text-align: center;
        color: $text-muted;
        text-style: italic;
    }
    EmployeeCard .status {
        text-align: center;
        margin: 1 0;
    }
    EmployeeCard .status-idle {
        color: $success;
    }
    EmployeeCard .status-working {
        color: $warning;
    }
    EmployeeCard .status-offline {
        color: $error;
    }
    EmployeeCard .task {
        text-align: center;
        color: $text-muted;
        height: 1;
    }
    EmployeeCard .actions {
        align: center middle;
        margin-top: 1;
    }
    """
    
    def __init__(
        self,
        employee_id: str,
        name: str,
        role: str,
        avatar: str = "👤",
        status: str = "idle",
        current_task: str = "",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.employee_id = employee_id
        self.name = name
        self.role = role
        self.avatar = avatar
        self.status = status
        self.current_task = current_task
    
    def compose(self):
        """组装卡片内容"""
        yield Static(self.avatar, classes="avatar")
        yield Static(self.name, classes="name")
        yield Static(self.role, classes="role")
        yield Static(self.status_icon + " " + self.status_text, classes=f"status status-{self.status}")
        if self.current_task:
            yield Static(self.current_task[:20] + "..." if len(self.current_task) > 20 else self.current_task, classes="task")
        with Horizontal(classes="actions"):
            yield Button("💬 对话", id=f"chat-{self.employee_id}", variant="primary")
            yield Button("📊 详情", id=f"detail-{self.employee_id}", variant="default")
    
    @property
    def status_icon(self) -> str:
        """根据状态返回图标"""
        icons = {
            "idle": "🟢",
            "working": "🟡",
            "offline": "🔴"
        }
        return icons.get(self.status, "⚪")
    
    @property
    def status_text(self) -> str:
        """返回状态文本"""
        texts = {
            "idle": "空闲",
            "working": "工作中",
            "offline": "离线"
        }
        return texts.get(self.status, "未知")
    
    def watch_status(self, status: str):
        """监听状态变化，更新显示"""
        try:
            status_widget = self.query_one(".status", Static)
            status_widget.update(self.status_icon + " " + self.status_text)
            status_widget.remove_class("status-idle")
            status_widget.remove_class("status-working")
            status_widget.remove_class("status-offline")
            status_widget.add_class(f"status-{status}")
        except Exception:
            pass
    
    def watch_current_task(self, task: str):
        """监听任务变化"""
        try:
            task_widget = self.query_one(".task", Static)
            display = task[:20] + "..." if len(task) > 20 else task
            task_widget.update(display)
        except Exception:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        if button_id == f"chat-{self.employee_id}":
            self.app.push_screen("chat", {"employee_id": self.employee_id})
        elif button_id == f"detail-{self.employee_id}":
            self.app.show_employee_detail(self.employee_id)
