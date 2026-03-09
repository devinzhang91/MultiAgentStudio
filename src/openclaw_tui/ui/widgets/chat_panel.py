"""聊天面板组件 - 平面风格"""
from textual.widgets import Static, Input, RichLog
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from rich.text import Text
from rich.markdown import Markdown
from datetime import datetime


class ChatPanel(Vertical):
    """聊天面板 - 扁平化对话界面"""
    
    messages = reactive(list)
    employee_name = reactive("")
    is_typing = reactive(False)
    
    DEFAULT_CSS = """
    ChatPanel {
        width: 100%;
        height: 100%;
        padding: 0;
    }
    ChatPanel .chat-header {
        height: 3;
        background: $primary-darken-3;
        content-align: center middle;
        text-style: bold;
        border-bottom: solid $primary-darken-2;
    }
    ChatPanel .messages-area {
        height: 1fr;
        background: $surface-darken-1;
        padding: 1;
    }
    ChatPanel .input-area {
        height: 3;
        background: $surface;
        border-top: solid $primary-darken-2;
    }
    ChatPanel .input-area Input {
        width: 1fr;
        border: none;
        background: $surface;
    }
    ChatPanel .typing-indicator {
        color: $text-muted;
        text-style: italic;
    }
    """
    
    def __init__(self, employee_id: str = "", employee_name: str = "", **kwargs):
        super().__init__(**kwargs)
        self.employee_id = employee_id
        self.employee_name = employee_name
        self.messages = []
    
    def compose(self):
        """组装聊天界面"""
        yield Static(f"🦞 {self.employee_name}", classes="chat-header")
        yield RichLog(classes="messages-area", id="chat-messages", wrap=True)
        with Horizontal(classes="input-area"):
            yield Input(placeholder="💭 输入消息或命令...", id="chat-input")
    
    def add_message(self, sender: str, content: str, is_user: bool = False):
        """添加消息到聊天"""
        timestamp = datetime.now().strftime("%H:%M")
        
        message = {
            "sender": sender,
            "content": content,
            "is_user": is_user,
            "timestamp": timestamp
        }
        self.messages.append(message)
        
        # 更新显示
        log = self.query_one("#chat-messages", RichLog)
        
        if is_user:
            header = Text(f"🧑 你 · {timestamp}", style="cyan bold")
        else:
            header = Text(f"🦞 {sender} · {timestamp}", style="green bold")
        
        log.write(header)
        log.write(content)
        log.write("")
    
    def show_typing(self, show: bool = True):
        """显示/隐藏正在输入提示"""
        log = self.query_one("#chat-messages", RichLog)
        if show:
            log.write(Text("🦞 正在输入...", style="dim italic"))
        self.is_typing = show
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入框回车"""
        if event.input.id == "chat-input":
            self.send_message()
    
    def send_message(self):
        """发送消息"""
        input_widget = self.query_one("#chat-input", Input)
        content = input_widget.value.strip()
        if content:
            self.add_message("你", content, is_user=True)
            input_widget.value = ""
            
            # 显示正在输入
            self.show_typing(True)
            
            # 通知 app 发送
            self.app.send_to_employee(self.employee_id, content)
