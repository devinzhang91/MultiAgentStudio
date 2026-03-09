"""主面板 - 员工列表 + 管理功能"""
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Input, Label, Switch
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive


class EmployeeCard(Vertical):
    """员工卡片"""
    
    DEFAULT_CSS = """
    EmployeeCard {
        width: 28;
        height: 12;
        background: $surface;
        border: solid $primary-darken-2;
        padding: 0;
        margin: 0 1 1 0;
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
        height: 6;
        padding: 0 1;
        content-align: center middle;
    }
    EmployeeCard .card-footer {
        height: 3;
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
    """
    
    def __init__(self, employee: dict, **kwargs):
        super().__init__(**kwargs)
        self.emp = employee
        self.can_focus = True
    
    def compose(self):
        emp = self.emp
        status = emp.get("status", "offline")
        status_emoji = {"idle": "🟢", "working": "🟡", "offline": "⚫", "error": "🔴"}.get(status, "⚪")
        status_text = {"idle": "空闲", "working": "工作中", "offline": "离线", "error": "错误"}.get(status, "未知")
        
        header_text = f"{status_emoji} {status_text}"
        unread = emp.get("unread_count", 0)
        if unread > 0:
            header_text += f" 💬{unread}"
        
        yield Static(header_text, classes="card-header")
        
        with Vertical(classes="card-body"):
            yield Static("🦞", classes="emoji-icon")
            yield Static(emp.get("name", "Unknown"), classes="name-text")
            yield Static(emp.get("role", ""), classes="role-text")
        
        task = emp.get("current_task", "") or "无任务"
        task_display = task[:14] + "..." if len(task) > 14 else task
        yield Static(f"📋 {task_display}", classes="card-footer")
    
    def on_click(self):
        self.app.open_chat(self.emp.get("id"))
    
    def on_key(self, event):
        if event.key == "enter":
            self.app.open_chat(self.emp.get("id"))
        elif event.key == "space":
            self.app.show_employee_detail(self.emp.get("id"))


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
            self.create_employee()
    
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


class DashboardScreen(Screen):
    """主面板"""
    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("r", "refresh", "刷新"),
        ("a", "add_employee", "添加员工"),
        ("?", "show_help", "帮助"),
    ]
    
    # 使用 reactive 变量
    employees = reactive(list)
    connection_status = reactive("🟡 连接中...")
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Vertical(classes="main"):
            with Horizontal(classes="toolbar"):
                yield Button("🔄 刷新 (r)", id="refresh", variant="primary")
                yield Button("➕ 添加员工 (a)", id="add", variant="success")
                yield Button("❓ 帮助 (?)", id="help", variant="default")
            
            yield Static("🦞 OpenClaw 工作室 - 点击卡片对话，Space 查看属性", classes="subtitle")
            
            # 员工卡片区域
            with Vertical(id="employee-container"):
                pass  # 动态填充
            
            with Horizontal(classes="status-bar"):
                yield Static(self.connection_status, id="conn-status")
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
        layout: grid;
        grid-size: 4;
        grid-columns: 1fr 1fr 1fr 1fr;
        grid-gutter: 1;
    }
    DashboardScreen .status-bar {
        height: 1; background: $primary-darken-3;
        padding: 0 2; align: left middle;
    }
    """
    
    def on_mount(self):
        """挂载后自动加载数据"""
        self.load_employees()
    
    async def load_employees(self):
        """异步加载员工列表"""
        try:
            data = await self.app.client.get_employees()
            self.employees = data  # 这会触发 watch_employees
            self.connection_status = "🟢 已连接"
        except Exception as e:
            print(f"[Dashboard] 加载失败: {e}")
            self.connection_status = f"🔴 错误: {e}"
    
    def watch_employees(self, employees):
        """监听 employees 变化，更新显示"""
        try:
            container = self.query_one("#employee-container")
            
            # 清空现有内容
            for child in list(container.children):
                child.remove()
            
            # 添加员工卡片
            for emp in employees:
                container.mount(EmployeeCard(emp))
            
            # 更新计数
            online = sum(1 for e in employees if e.get("status") != "offline")
            self.query_one("#emp-count", Static).update(f"🦞 {online}/{len(employees)}")
            
        except Exception as e:
            print(f"[Dashboard] 更新显示错误: {e}")
    
    def watch_connection_status(self, status):
        """监听连接状态变化"""
        try:
            self.query_one("#conn-status", Static).update(status)
        except:
            pass
    
    def on_button_pressed(self, event):
        if event.button.id == "refresh":
            self.load_employees()
        elif event.button.id == "add":
            self.push_screen(AddEmployeeScreen())
        elif event.button.id == "help":
            self.show_help()
    
    def action_refresh(self):
        self.load_employees()
    
    def action_add_employee(self):
        self.push_screen(AddEmployeeScreen())
    
    def show_help(self):
        help_text = """
🖱️ 鼠标:
  点击卡片   进入对话
  点击按钮   执行操作

⌨️ 键盘:
  Enter      进入对话
  Space      查看属性
  a          添加新员工
  r          刷新列表
  q          退出
"""
        self.notify(help_text, severity="information", timeout=15)
