"""员工属性界面"""
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Label
from textual.containers import Horizontal, Vertical, Container, Grid


class EmployeePropertyScreen(Screen):
    """员工属性界面"""
    
    BINDINGS = [("escape, q", "go_back", "返回")]
    
    def __init__(self, employee: dict, **kwargs):
        super().__init__(**kwargs)
        self.employee = employee
        self.config = employee.get("config", {})
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Container(classes="container"):
            yield Static(f"🦞 员工属性 - {self.employee.get('name', 'Unknown')}", classes="title")
            
            with Grid(classes="form-grid"):
                yield Label("ID:"); yield Static(self.employee.get("id", ""))
                yield Label("名称:"); yield Static(self.employee.get("name", ""))
                yield Label("角色:"); yield Static(self.employee.get("role", ""))
                yield Label("状态:"); yield Static(self.employee.get("status", ""))
                yield Label("当前任务:"); yield Static(self.employee.get("current_task") or "无")
                
                yield Static("", classes="divider"); yield Static("")
                yield Label("OpenClaw 配置", classes="section-title"); yield Static("")
                
                yield Label("Base URL:"); yield Static(self.config.get("base_url", "未配置"))
                yield Label("Token:"); 
                token = self.config.get("token", "")
                yield Static(f"{token[:10]}..." if len(token) > 10 else (token or "未配置"))
                yield Label("Session Key:"); yield Static(self.config.get("session_key", "default"))
                yield Label("Timeout:"); yield Static(f"{self.config.get('timeout', 120)} 秒")
                yield Label("Enabled:"); yield Static("✅ 启用" if self.config.get("enabled") else "❌ 禁用")
                
                yield Static("", classes="divider"); yield Static("")
                yield Label("创建时间:"); yield Static(self.employee.get("created_at", "")[:19])
                yield Label("更新时间:"); yield Static(self.employee.get("updated_at", "")[:19])
            
            with Horizontal(classes="button-row"):
                yield Button("← 返回", id="back", variant="default")
                yield Button("🔄 重启连接", id="restart", variant="primary")
                yield Button("🗑️ 删除员工", id="delete", variant="error")
        
        yield Footer()
    
    DEFAULT_CSS = """
    EmployeePropertyScreen { align: center middle; }
    EmployeePropertyScreen .container { 
        width: 80; height: auto; max-height: 90%;
        border: solid $primary; padding: 1 2;
    }
    EmployeePropertyScreen .title { 
        text-style: bold; height: 3;
        content-align: center middle;
        border-bottom: solid $primary-darken-2;
    }
    EmployeePropertyScreen .form-grid {
        grid-size: 2; grid-columns: 15 1fr;
        grid-gutter: 1; padding: 1 0; height: auto;
    }
    EmployeePropertyScreen .section-title {
        text-style: bold; color: $accent; column-span: 2;
    }
    EmployeePropertyScreen .divider {
        height: 1; background: $primary-darken-2; column-span: 2;
    }
    EmployeePropertyScreen .button-row {
        height: 3; align: center middle; margin-top: 1;
    }
    EmployeePropertyScreen .button-row Button { margin: 0 1; }
    """
    
    def on_button_pressed(self, event):
        if event.button.id == "back":
            self.action_go_back()
        elif event.button.id == "restart":
            self.restart_connection()
        elif event.button.id == "delete":
            self.delete_employee()
    
    async def restart_connection(self):
        self.notify("🔄 正在重启连接...")
        try:
            await self.app.client.post(f"/api/employees/{self.employee['id']}/restart")
            self.notify("✅ 连接已重启")
        except Exception as e:
            self.notify(f"❌ 重启失败: {e}", severity="error")
    
    async def delete_employee(self):
        self.notify("🗑️ 删除员工...")
        try:
            await self.app.client.delete(f"/api/employees/{self.employee['id']}")
            self.notify("✅ 员工已删除")
            self.action_go_back()
        except Exception as e:
            self.notify(f"❌ 删除失败: {e}", severity="error")
    
    def action_go_back(self):
        self.app.pop_screen()
