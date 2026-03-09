"""聊天屏幕"""
from textual.screen import Screen
from textual.widgets import Button, Static
from textual.containers import Horizontal, Vertical

from ..widgets.chat_panel import ChatPanel


class ChatScreen(Screen):
    """聊天界面 - 与特定员工对话"""
    
    DEFAULT_CSS = """
    ChatScreen {
        align: center middle;
    }
    ChatScreen .chat-container {
        width: 80%;
        height: 80%;
        border: solid $primary;
        background: $surface-darken-1;
    }
    ChatScreen .chat-header {
        height: 3;
        background: $primary-darken-2;
        content-align: center middle;
        text-style: bold;
    }
    ChatScreen .back-btn {
        width: auto;
        margin: 0 1;
    }
    """
    
    def __init__(self, employee_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.employee_id = employee_id
        self.employee = self.get_employee_info(employee_id)
    
    def get_employee_info(self, employee_id: str) -> dict:
        """获取员工信息"""
        # TODO: 从状态管理器获取
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
            with Horizontal(classes="chat-header"):
                yield Button("← 返回", id="back-btn", classes="back-btn", variant="default")
                yield Static(f"与 {self.employee['name']} 对话 - {self.employee['role']}", expand=True)
            
            yield ChatPanel(
                employee_id=self.employee_id,
                employee_name=self.employee['name']
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "back-btn":
            self.app.pop_screen()
    
    def on_chat_message(self, message: str):
        """接收来自员工的消息"""
        chat_panel = self.query_one(ChatPanel)
        chat_panel.add_message(self.employee['name'], message, is_user=False)
