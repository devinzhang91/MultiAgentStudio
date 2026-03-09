"""聊天界面"""
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Input, Button, RichLog
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual import work


class ChatScreen(Screen):
    """与员工对话界面"""
    
    BINDINGS = [
        ("escape, q", "go_back", "返回"),
    ]
    
    employee_id = reactive("")
    employee_name = reactive("")
    messages = reactive(list)
    
    def __init__(self, employee_id: str, **kwargs):
        super().__init__(**kwargs)
        self.employee_id = employee_id
        self.messages = []
        self.employee_name = ""
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Vertical(classes="container"):
            with Horizontal(classes="toolbar"):
                yield Button("← 返回 (Esc)", id="back", variant="default")
                yield Static(f"🦞 与 {self.employee_name} 对话", id="title")
            
            yield RichLog(id="messages", classes="messages")
            
            with Horizontal(classes="input-area"):
                yield Input(placeholder="输入消息，Enter 发送...", id="message-input")
                yield Button("发送", id="send", variant="primary")
        
        yield Footer()
    
    DEFAULT_CSS = """
    ChatScreen { layout: vertical; }
    ChatScreen .container { height: 1fr; }
    ChatScreen .toolbar {
        height: 3; background: $primary-darken-3;
        padding: 0 2; align: left middle;
    }
    ChatScreen #title {
        margin-left: 2;
        text-style: bold;
        content-align: center middle;
    }
    ChatScreen .messages {
        height: 1fr;
        background: $surface-darken-1;
        padding: 1 2;
        border-bottom: solid $primary-darken-2;
    }
    ChatScreen .input-area {
        height: 3; padding: 0 2; align: left middle;
    }
    ChatScreen .input-area Input { width: 1fr; }
    ChatScreen .input-area Button { margin-left: 1; }
    """
    
    def on_mount(self):
        self.load_employee_info()
        self.load_messages()
        self.query_one("#message-input", Input).focus()
    
    @work(exclusive=True)
    async def load_employee_info(self):
        try:
            emp = await self.app.client.get_employee(self.employee_id)
            if emp:
                self.employee_name = emp.get("name", "Unknown")
                self.query_one("#title", Static).update(f"🦞 与 {self.employee_name} 对话")
        except Exception as e:
            self.notify(f"加载失败: {e}", severity="error")
    
    @work(exclusive=True)
    async def load_messages(self):
        try:
            msgs = await self.app.client.get_messages(self.employee_id)
            self.messages = msgs
            self.update_messages_display()
        except Exception as e:
            self.notify(f"加载消息失败: {e}", severity="error")
    
    def update_messages_display(self):
        log = self.query_one("#messages", RichLog)
        log.clear()
        
        for msg in self.messages:
            is_user = msg.get("is_user", False)
            sender = "🧑 你" if is_user else f"🦞 {self.employee_name}"
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")[11:16] if msg.get("timestamp") else ""
            
            log.write(f"{sender} · {timestamp}")
            log.write(content)
            log.write("")
    
    def on_button_pressed(self, event):
        if event.button.id == "back":
            self.action_go_back()
        elif event.button.id == "send":
            self.send_message()
    
    def on_input_submitted(self, event):
        if event.input.id == "message-input":
            self.send_message()
    
    @work(exclusive=True)
    async def send_message(self):
        input_widget = self.query_one("#message-input", Input)
        content = input_widget.value.strip()
        if not content:
            return
        
        input_widget.value = ""
        
        # 添加到本地显示
        self.messages.append({
            "content": content,
            "is_user": True,
            "timestamp": "",
        })
        self.update_messages_display()
        
        # 发送到后端
        try:
            response = await self.app.client.send_message(self.employee_id, content)
            if response:
                # 重新加载消息获取完整列表
                await self.load_messages()
        except Exception as e:
            self.notify(f"发送失败: {e}", severity="error")
    
    def action_go_back(self):
        self.app.pop_screen()

    def watch_messages(self, messages):
        self.update_messages_display()
