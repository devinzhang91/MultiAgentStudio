"""聊天面板组件"""
from textual.widgets import Static, Input, Button, RichLog
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from rich.markdown import Markdown
from rich.text import Text
from datetime import datetime


class ChatPanel(Vertical):
    """聊天面板 - 与员工对话的界面"""
    
    messages = reactive(list)
    employee_name = reactive("")
    
    DEFAULT_CSS = """
    ChatPanel {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    ChatPanel .header {
        height: 3;
        content-align: center middle;
        border-bottom: solid $primary;
        text-style: bold;
    }
    ChatPanel .messages {
        height: 1fr;
        border: solid $primary-darken-2;
        padding: 1;
        overflow-y: auto;
    }
    ChatPanel .input-area {
        height: 3;
        margin-top: 1;
    }
    ChatPanel .input-area Input {
        width: 1fr;
    }
    ChatPanel .input-area Button {
        width: auto;
    }
    """
    
    def __init__(self, employee_id: str = "", employee_name: str = "", **kwargs):
        super().__init__(**kwargs)
        self.employee_id = employee_id
        self.employee_name = employee_name
        self.messages = []
    
    def compose(self):
        """组装聊天界面"""
        yield Static(f"💬 与 {self.employee_name} 对话", classes="header")
        yield RichLog(classes="messages", id="chat-messages")
        with Horizontal(classes="input-area"):
            yield Input(placeholder=f"@{self.employee_name.lower()} 输入命令...", id="chat-input")
            yield Button("发送", id="send-btn", variant="primary")
    
    def add_message(self, sender: str, content: str, is_user: bool = False):
        """添加消息到聊天"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = "🧑 You" if is_user else f"🤖 {sender}"
        message = {
            "sender": sender,
            "content": content,
            "is_user": is_user,
            "timestamp": timestamp
        }
        self.messages.append(message)
        
        # 更新显示
        log = self.query_one("#chat-messages", RichLog)
        header = Text(f"{prefix}  {timestamp}", style="bold cyan" if is_user else "bold green")
        log.write(header)
        log.write(Markdown(content))
        log.write("")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理发送按钮"""
        if event.button.id == "send-btn":
            self.send_message()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入框回车"""
        if event.input.id == "chat-input":
            self.send_message()
    
    def send_message(self):
        """发送消息"""
        input_widget = self.query_one("#chat-input", Input)
        content = input_widget.value.strip()
        if content:
            self.add_message("You", content, is_user=True)
            input_widget.value = ""
            
            # 通知 app 发送 webhook
            self.app.send_to_employee(self.employee_id, content)
