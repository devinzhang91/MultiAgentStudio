"""聊天屏幕 - 支持键盘导航"""
from textual.screen import Screen
from textual.widgets import Button, Static, Input
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive

from ..widgets.chat_panel import ChatPanel


class ChatScreen(Screen):
    """聊天界面 - 与特定员工对话，支持键盘导航"""
    
    DEFAULT_CSS = """
    ChatScreen {
        align: center middle;
    }
    ChatScreen .chat-container {
        width: 85%;
        height: 85%;
        border: solid $primary-darken-2;
        background: $surface;
    }
    ChatScreen .chat-toolbar {
        height: 3;
        background: $primary-darken-3;
        content-align: left middle;
        padding: 0 1;
    }
    ChatScreen .back-btn {
        width: auto;
        min-width: 8;
    }
    ChatScreen .back-btn:focus {
        background: $accent;
    }
    ChatScreen .title-text {
        text-style: bold;
        margin-left: 2;
        content-align: center middle;
    }
    ChatScreen .chat-body {
        height: 1fr;
    }
    ChatScreen .nav-hint {
        height: 1;
        background: $surface-darken-1;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
    }
    """
    
    BINDINGS = [
        ("escape", "go_back", "返回"),
        ("ctrl+c", "go_back", "返回"),
    ]
    
    def __init__(self, employee_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.employee_id = employee_id
        self.employee = self.get_employee_info(employee_id)
    
    def get_employee_info(self, employee_id: str) -> dict:
        employees = {
            "alice-001": {"name": "Alice", "role": "代码审查专家"},
            "bob-002": {"name": "Bob", "role": "文档生成助手"},
            "carol-003": {"name": "Carol", "role": "测试工程师"},
            "dave-004": {"name": "Dave", "role": "DevOps 专家"},
            "eve-005": {"name": "Eve", "role": "数据分析助手"},
        }
        return employees.get(employee_id, {"name": "Unknown", "role": ""})
    
    def compose(self):
        """组装聊天界面"""
        with Vertical(classes="chat-container"):
            with Horizontal(classes="chat-toolbar"):
                yield Button("← 返回", id="back-btn", classes="back-btn", variant="default")
                yield Static(f"🦞 与 {self.employee['name']} 对话 ({self.employee['role']})", classes="title-text")
            
            with Vertical(classes="chat-body"):
                yield ChatPanel(
                    employee_id=self.employee_id,
                    employee_name=self.employee['name']
                )
            
            yield Static("Tab 切换 │ Enter 发送 │ Esc 返回工作室", classes="nav-hint")
    
    def on_mount(self):
        """挂载后聚焦输入框"""
        try:
            chat_panel = self.query_one(ChatPanel)
            input_widget = chat_panel.query_one("#chat-input", Input)
            input_widget.focus()
        except Exception:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.action_go_back()
    
    def action_go_back(self):
        """返回工作室"""
        self.app.pop_screen()
    
    def on_chat_message(self, message: str):
        """接收来自员工的消息"""
        try:
            chat_panel = self.query_one(ChatPanel)
            chat_panel.show_typing(False)
            chat_panel.add_message(self.employee['name'], message, is_user=False)
        except Exception:
            pass
    
    def on_key(self, event):
        """处理键盘事件"""
        if event.key == "escape":
            self.action_go_back()
            event.stop()
