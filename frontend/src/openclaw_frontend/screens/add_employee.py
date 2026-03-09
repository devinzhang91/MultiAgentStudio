"""添加员工界面"""
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Input, Label, Switch
from textual.containers import Horizontal, Vertical, Container


class AddEmployeeScreen(Screen):
    """添加员工界面"""
    
    BINDINGS = [("escape, q", "go_back", "返回")]
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Container(classes="container"):
            yield Static("🦞 添加新员工", classes="title")
            
            with Vertical(classes="form"):
                yield Label("基本信息", classes="section-title")
                yield Input(placeholder="员工名称 *", id="name")
                yield Input(placeholder="角色（如：代码审查专家）", id="role", value="OpenClaw 员工")
                
                yield Static("", classes="divider")
                yield Label("OpenClaw 连接配置", classes="section-title")
                yield Input(placeholder="Base URL * (如: wss://gateway.openclaw.com)", id="base_url")
                yield Input(placeholder="Token *", id="token", password=True)
                yield Input(placeholder="Session Key", id="session_key", value="default")
                yield Input(placeholder="超时时间（秒）", id="timeout", value="120")
                
                with Horizontal(classes="switch-row"):
                    yield Label("启用连接:")
                    yield Switch(id="enabled", value=True)
            
            with Horizontal(classes="button-row"):
                yield Button("← 返回", id="back", variant="default")
                yield Button("✅ 创建员工", id="create", variant="primary")
        
        yield Footer()
    
    DEFAULT_CSS = """
    AddEmployeeScreen { align: center middle; }
    AddEmployeeScreen .container { 
        width: 80; height: auto; border: solid $primary; padding: 1 2;
    }
    AddEmployeeScreen .title { 
        text-style: bold; height: 3;
        content-align: center middle;
        border-bottom: solid $primary-darken-2;
    }
    AddEmployeeScreen .form { height: auto; padding: 1 0; }
    AddEmployeeScreen .section-title {
        text-style: bold; color: $accent; margin: 1 0;
    }
    AddEmployeeScreen .divider {
        height: 1; background: $primary-darken-2; margin: 1 0;
    }
    AddEmployeeScreen Input { margin: 1 0; }
    AddEmployeeScreen .switch-row { height: 3; align: left middle; }
    AddEmployeeScreen .switch-row Label { margin-right: 2; }
    AddEmployeeScreen .button-row {
        height: 3; align: center middle; margin-top: 1;
    }
    AddEmployeeScreen .button-row Button { margin: 0 1; }
    """
    
    def on_button_pressed(self, event):
        if event.button.id == "back":
            self.action_go_back()
        elif event.button.id == "create":
            self.run_worker(self.create_employee)
    
    async def create_employee(self):
        name = self.query_one("#name", Input).value.strip()
        role = self.query_one("#role", Input).value.strip()
        base_url = self.query_one("#base_url", Input).value.strip()
        token = self.query_one("#token", Input).value.strip()
        session_key = self.query_one("#session_key", Input).value.strip()
        timeout_str = self.query_one("#timeout", Input).value.strip()
        enabled = self.query_one("#enabled", Switch).value
        
        if not name:
            self.notify("❌ 请输入员工名称", severity="error"); return
        if not base_url:
            self.notify("❌ 请输入 Base URL", severity="error"); return
        if not token:
            self.notify("❌ 请输入 Token", severity="error"); return
        
        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 120
        
        data = {
            "name": name,
            "role": role,
            "config": {
                "base_url": base_url,
                "token": token,
                "session_key": session_key,
                "timeout": timeout,
                "enabled": enabled,
            }
        }
        
        self.notify("📝 创建员工...")
        try:
            await self.app.client.post("/api/employees", json=data)
            self.notify(f"✅ 员工 '{name}' 创建成功!")
            self.action_go_back()
        except Exception as e:
            self.notify(f"❌ 创建失败: {e}", severity="error")
    
    def action_go_back(self):
        self.app.pop_screen()
