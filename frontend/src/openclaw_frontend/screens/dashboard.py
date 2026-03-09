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
        height: 14;
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


class DashboardScreen(Screen):
    """主面板"""
    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("r", "action_refresh", "刷新"),
        ("a", "action_add_employee", "添加员工"),
        ("?", "action_show_help", "帮助"),
    ]
    
    employees = reactive(list)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.employees = []
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Vertical(classes="main"):
            with Horizontal(classes="toolbar"):
                yield Button("🔄 刷新 (r)", id="refresh-btn", variant="primary")
                yield Button("➕ 添加员工 (a)", id="add-btn", variant="success")
                yield Button("❓ 帮助 (?)", id="help-btn", variant="default")
            
            yield Static("🦞 OpenClaw 工作室", classes="title")
            yield Static("点击卡片进入对话，按 Space 查看属性", classes="subtitle")
            
            # 员工列表容器
            with Vertical(id="employee-list"):
                yield Static("加载中...", id="loading-text")
            
            with Horizontal(classes="status-bar"):
                yield Static("🟡 连接中...", id="status-text")
                yield Static("", id="count-text")
        
        yield Footer()
    
    DEFAULT_CSS = """
    DashboardScreen { layout: vertical; }
    DashboardScreen .main { height: 1fr; }
    DashboardScreen .toolbar {
        height: 3; 
        background: $surface-darken-1;
        padding: 0 2;
        align: left middle;
    }
    DashboardScreen .toolbar Button { 
        margin-right: 1; 
    }
    DashboardScreen .title {
        height: 2;
        text-style: bold;
        padding: 0 2;
        content-align: center middle;
    }
    DashboardScreen .subtitle {
        height: 1; 
        padding: 0 2; 
        color: $text-muted;
        content-align: center middle;
    }
    DashboardScreen #employee-list {
        height: 1fr;
        padding: 1 2;
        layout: grid;
        grid-size: 4;
        grid-columns: 1fr 1fr 1fr 1fr;
        grid-gutter: 1;
    }
    DashboardScreen #loading-text {
        column-span: 4;
        content-align: center middle;
        color: $text-muted;
    }
    DashboardScreen .status-bar {
        height: 1; 
        background: $primary-darken-3;
        padding: 0 2; 
        align: left middle;
    }
    """
    
    async def on_mount(self):
        """挂载后加载数据"""
        print("[Dashboard] on_mount 被调用")
        await self.load_employees()
    
    async def load_employees(self):
        """加载员工列表"""
        print("[Dashboard] 开始加载员工...")
        try:
            data = await self.app.client.get_employees()
            print(f"[Dashboard] 加载到 {len(data)} 个员工: {[e.get('name') for e in data]}")
            # 直接更新 UI
            self.update_employee_list(data)
        except Exception as e:
            print(f"[Dashboard] 加载失败: {e}")
            import traceback
            traceback.print_exc()
            self.update_status(f"🔴 错误: {e}")
    
    def update_employee_list(self, employees):
        """更新员工列表显示"""
        print(f"[Dashboard] update_employee_list: {len(employees)} 个员工")
        
        try:
            # 获取容器
            container = self.query_one("#employee-list")
            print(f"[Dashboard] 找到容器: {container}, 类型: {type(container)}")
            
            # 清空现有内容（保留 loading-text）
            removed = 0
            for child in list(container.children):
                if child.id != "loading-text":
                    child.remove()
                    removed += 1
            print(f"[Dashboard] 清空完成，移除了 {removed} 个子元素")
            
            # 隐藏加载文本
            try:
                loading = container.query_one("#loading-text")
                loading.styles.display = "none"
                print("[Dashboard] 隐藏 loading")
            except Exception as e:
                print(f"[Dashboard] 隐藏 loading 失败: {e}")
            
            # 添加员工卡片
            if employees:
                print(f"[Dashboard] 开始添加 {len(employees)} 个卡片")
                for i, emp in enumerate(employees):
                    try:
                        print(f"[Dashboard] 创建卡片 {i}: {emp.get('name')}")
                        card = EmployeeCard(emp)
                        print(f"[Dashboard] 卡片创建成功，准备 mount")
                        container.mount(card)
                        print(f"[Dashboard] 卡片 {i} mount 成功")
                    except Exception as e:
                        print(f"[Dashboard] 添加卡片 {i} 失败: {e}")
                        import traceback
                        traceback.print_exc()
                
                print("[Dashboard] 所有卡片添加完成")
                
                # 更新状态
                self.update_status("🟢 已连接")
                online = sum(1 for e in employees if e.get("status") != "offline")
                self.update_count(f"🦞 {online}/{len(employees)}")
            else:
                self.update_status("⚠️ 无员工")
                self.update_count("")
                
                # 显示空提示
                container.mount(Static("暂无员工，按 'a' 添加", classes="empty-hint"))
                
        except Exception as e:
            print(f"[Dashboard] update_employee_list 错误: {e}")
            import traceback
            traceback.print_exc()
    
    def watch_employees(self, employees):
        """监听员工数据变化（备用）"""
        print(f"[Dashboard] watch_employees 被调用，{len(employees)} 个员工")
        if self.is_mounted:
            self.update_employee_list(employees)
    
    def update_status(self, text: str):
        """更新状态文本"""
        try:
            status = self.query_one("#status-text", Static)
            status.update(text)
        except Exception as e:
            print(f"[Dashboard] 更新状态失败: {e}")
    
    def update_count(self, text: str):
        """更新计数文本"""
        try:
            count = self.query_one("#count-text", Static)
            count.update(text)
        except Exception as e:
            print(f"[Dashboard] 更新计数失败: {e}")
    
    def on_button_pressed(self, event):
        """按钮点击处理"""
        btn_id = event.button.id
        if btn_id == "refresh-btn":
            self.action_refresh()
        elif btn_id == "add-btn":
            self.action_add_employee()
        elif btn_id == "help-btn":
            self.action_show_help()
    
    def action_refresh(self):
        """刷新"""
        self.run_worker(self.load_employees)
    
    def action_add_employee(self):
        """添加员工"""
        from .add_employee import AddEmployeeScreen
        self.push_screen(AddEmployeeScreen())
    
    def action_show_help(self):
        """显示帮助"""
        help_text = """
🖱️ 鼠标操作:
  点击卡片     进入对话
  点击按钮     执行操作

⌨️ 键盘操作:
  Enter      进入对话
  Space      查看属性
  a          添加新员工
  r          刷新列表
  q          退出
"""
        self.notify(help_text, severity="information", timeout=15)
