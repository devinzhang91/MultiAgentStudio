"""主面板 - 员工列表 + 管理功能"""
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Input, Label, Switch, DataTable
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from textual import work
import asyncio


class EmployeeCard(Vertical):
    """员工卡片"""
    
    employee_id = reactive("")
    name = reactive("")
    role = reactive("")
    status = reactive("offline")
    current_task = reactive("")
    unread_count = reactive(0)
    connection_error = reactive(None)
    
    DEFAULT_CSS = """
    EmployeeCard {
        width: 30;
        height: 14;
        background: $surface;
        border: solid $primary-darken-2;
        padding: 0;
        cursor: pointer;
    }
    EmployeeCard:hover {
        background: $surface-lighten-1;
        border: solid $primary;
    }
    EmployeeCard:focus { border: solid $accent; }
    EmployeeCard .card-header {
        height: 3;
        background: $primary-darken-3;
        content-align: center middle;
    }
    EmployeeCard .card-body {
        height: 7;
        padding: 0 1;
        content-align: center middle;
    }
    EmployeeCard .card-footer {
        height: 2;
        content-align: center middle;
        color: $text-muted;
    }
    EmployeeCard .emoji-icon {
        text-style: bold;
        text-align: center;
    }
    EmployeeCard .name-text {
        text-style: bold;
        text-align: center;
    }
    EmployeeCard .role-text {
        text-align: center;
        color: $text-muted;
    }
    EmployeeCard .error-text {
        color: $error;
        text-align: center;
        text-style: italic;
    }
    """
    
    def __init__(self, employee: dict, **kwargs):
        super().__init__(**kwargs)
        self.employee_id = employee.get("id", "")
        self.name = employee.get("name", "Unknown")
        self.role = employee.get("role", "")
        self.status = employee.get("status", "offline")
        self.current_task = employee.get("current_task", "")
        self.unread_count = employee.get("unread_count", 0)
        self.connection_error = employee.get("connection_error")
        self.can_focus = True
    
    def compose(self):
        status_emoji = {"idle": "🟢", "working": "🟡", "offline": "⚫", "error": "🔴"}.get(self.status, "⚪")
        status_text = {"idle": "空闲", "working": "工作中", "offline": "离线", "error": "错误"}.get(self.status, "未知")
        
        header_text = f"{status_emoji} {status_text}"
        if self.unread_count > 0:
            header_text += f" 💬{self.unread_count}"
        
        yield Static(header_text, classes="card-header")
        
        with Vertical(classes="card-body"):
            yield Static("🦞", classes="emoji-icon")
            yield Static(self.name, classes="name-text")
            yield Static(self.role, classes="role-text")
            if self.connection_error:
                yield Static(f"⚠️ {self.connection_error[:20]}...", classes="error-text")
        
        task_display = self.current_task[:16] + "..." if len(self.current_task) > 16 else (self.current_task or "无任务")
        yield Static(f"📋 {task_display}", classes="card-footer")
    
    def on_click(self):
        self.app.open_chat(self.employee_id)
    
    def on_key(self, event):
        if event.key == "enter":
            self.app.open_chat(self.employee_id)
        elif event.key == "space":
            self.app.show_employee_detail(self.employee_id)


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
            yield Static(f"🦞 员工属性 - {self.employee.get('name')}", classes="title")
            
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
    
    @work(exclusive=True)
    async def restart_connection(self):
        self.notify("🔄 正在重启连接...")
        try:
            await self.app.client.post(f"/api/employees/{self.employee['id']}/restart")
            self.notify("✅ 连接已重启")
        except Exception as e:
            self.notify(f"❌ 重启失败: {e}", severity="error")
    
    @work(exclusive=True)
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
                yield Input(placeholder="角色（如：代码审查专家）", id="role")
                
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
            self.create_employee()
    
    @work(exclusive=True)
    async def create_employee(self):
        name = self.query_one("#name", Input).value.strip()
        role = self.query_one("#role", Input).value.strip() or "OpenClaw 员工"
        base_url = self.query_one("#base_url", Input).value.strip()
        token = self.query_one("#token", Input).value.strip()
        session_key = self.query_one("#session_key", Input).value.strip() or "default"
        timeout_str = self.query_one("#timeout", Input).value.strip() or "120"
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


class DashboardScreen(Screen):
    """主面板"""
    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("r", "refresh", "刷新"),
        ("a", "add_employee", "添加员工"),
        ("?", "show_help", "帮助"),
    ]
    
    employees = reactive(list)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.employees = []
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Vertical(classes="main"):
            with Horizontal(classes="toolbar"):
                yield Button("🔄 刷新 (r)", id="refresh", variant="primary")
                yield Button("➕ 添加员工 (a)", id="add", variant="success")
                yield Button("❓ 帮助 (?)", id="help", variant="default")
            
            yield Static("🦞 OpenClaw 工作室 - 点击卡片对话，Space 查看属性", classes="subtitle")
            
            # 员工卡片容器
            with Vertical(id="employee-container"):
                with Horizontal(id="employee-row-1"):
                    pass
                with Horizontal(id="employee-row-2"):
                    pass
            
            with Horizontal(classes="status-bar"):
                yield Static("🟡 连接中...", id="conn-status")
                yield Static("🦞 0", id="emp-count")
        
        yield Footer()
    
    DEFAULT_CSS = """
    DashboardScreen { layout: vertical; }
    DashboardScreen .main { height: 1fr; }
    DashboardScreen .toolbar {
        height: 3; background: $surface-darken-1;
        padding: 0 2; align: left middle;
    }
    DashboardScreen .toolbar Button { margin-right: 1; }
    DashboardScreen .subtitle {
        height: 2; padding: 0 2; color: $text-muted;
    }
    DashboardScreen #employee-container {
        height: 1fr;
        padding: 1 2;
    }
    DashboardScreen #employee-row-1, DashboardScreen #employee-row-2 {
        height: auto;
        align: left top;
    }
    DashboardScreen .status-bar {
        height: 1; background: $primary-darken-3;
        padding: 0 2; align: left middle;
    }
    """
    
    def on_mount(self):
        self.load_employees()
    
    @work(exclusive=True)
    async def load_employees(self):
        try:
            self.employees = await self.app.client.get_employees()
            print(f"[Dashboard] 加载到 {len(self.employees)} 个员工")
            
            # 使用 app.call_from_thread 在 UI 线程中更新
            def do_update():
                self.update_display()
                try:
                    self.query_one("#conn-status", Static).update("🟢 已连接")
                except:
                    pass
            
            self.app.call_from_thread(do_update)
        except Exception as e:
            print(f"[Dashboard] 加载失败: {e}")
            def do_error():
                try:
                    self.query_one("#conn-status", Static).update(f"🔴 错误: {e}")
                except:
                    pass
            self.app.call_from_thread(do_error)
    
    def update_display(self):
        try:
            # 获取行容器
            row1 = self.query_one("#employee-row-1")
            row2 = self.query_one("#employee-row-2")
            
            # 清空现有卡片
            for child in list(row1.children):
                child.remove()
            for child in list(row2.children):
                child.remove()
            
            # 添加员工卡片（每行4个）
            for i, emp in enumerate(self.employees):
                card = EmployeeCard(emp)
                if i < 4:
                    row1.mount(card)
                else:
                    row2.mount(card)
            
            online = sum(1 for e in self.employees if e.get("status") != "offline")
            self.query_one("#emp-count", Static).update(f"🦞 {online}/{len(self.employees)}")
        except Exception as e:
            print(f"[Dashboard] 更新显示错误: {e}")
    
    def on_button_pressed(self, event):
        if event.button.id == "refresh":
            self.load_employees()
        elif event.button.id == "add":
            self.action_add_employee()
        elif event.button.id == "help":
            self.action_show_help()
    
    def action_refresh(self):
        self.load_employees()
    
    def action_add_employee(self):
        self.app.push_screen(AddEmployeeScreen())
    
    def action_show_help(self):
        help_text = """
🖱️ 鼠标:
  点击卡片   进入对话
  点击按钮   执行操作

⌨️ 键盘:
  Enter      进入对话
  Space      查看属性/删除/重启
  a          添加新员工
  r          刷新列表
  q          退出

配置项:
  - Base URL: OpenClaw Gateway 地址
  - Token: 认证令牌
  - Session Key: 会话标识
  - Timeout: 请求超时时间
"""
        self.notify(help_text, severity="information", timeout=20)
    
    def watch_employees(self, employees):
        # 当 employees 变化时，如果 UI 已挂载则更新
        if self.is_mounted:
            self.update_display()
