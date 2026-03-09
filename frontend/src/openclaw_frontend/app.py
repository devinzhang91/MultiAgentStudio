"""
OpenClaw TUI Frontend - TUI 前端
连接后端服务，纯展示和交互
"""
import asyncio
from typing import Optional, List, Dict

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Horizontal, Vertical

from .api_client import BackendClient

# 后端地址
BACKEND_API = "http://localhost:18765"
BACKEND_WS = "ws://localhost:18765/ws"


class EmployeeCard(Vertical):
    """员工卡片组件"""
    
    employee_id = reactive("")
    name = reactive("")
    role = reactive("")
    status = reactive("idle")
    current_task = reactive("")
    unread_count = reactive(0)
    selected = reactive(False)
    
    DEFAULT_CSS = """
    EmployeeCard {
        width: 28;
        height: 12;
        background: $surface;
        border: solid $primary-darken-2;
        padding: 0;
        cursor: pointer;
    }
    EmployeeCard:hover {
        background: $surface-lighten-1;
        border: solid $primary;
    }
    EmployeeCard:focus {
        border: solid $accent;
        background: $surface-lighten-2;
    }
    EmployeeCard.selected {
        border: solid $accent;
        background: $primary-darken-3;
    }
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
    }
    """
    
    def __init__(self, employee: Dict, **kwargs):
        super().__init__(**kwargs)
        self.employee_id = employee.get("id", "")
        self.name = employee.get("name", "Unknown")
        self.role = employee.get("role", "")
        self.status = employee.get("status", "idle")
        self.current_task = employee.get("current_task", "")
        self.unread_count = employee.get("unread_count", 0)
        self.can_focus = True
    
    def compose(self):
        status_emoji = {"idle": "🟢", "working": "🟡", "offline": "⚫"}.get(self.status, "⚪")
        status_text = {"idle": "空闲", "working": "工作中", "offline": "离线"}.get(self.status, "未知")
        
        header_text = f"{status_emoji} {status_text}"
        if self.unread_count > 0:
            header_text += f"  💬{self.unread_count}"
        
        yield Static(header_text, classes="card-header")
        
        with Vertical(classes="card-body"):
            yield Static("🦞", classes="emoji-icon")
            yield Static(self.name, classes="name-text")
            yield Static(self.role, classes="role-text")
        
        task_display = self.current_task[:12] + "..." if len(self.current_task) > 12 else (self.current_task or "无任务")
        yield Static(f"📋 {task_display}", classes="card-footer")
    
    def update_from_data(self, data: Dict):
        """从数据更新"""
        self.status = data.get("status", self.status)
        self.current_task = data.get("current_task", self.current_task)
        self.unread_count = data.get("unread_count", self.unread_count)
        self.refresh()
    
    def on_click(self):
        """点击进入对话"""
        self.app.open_chat(self.employee_id)
    
    def on_key(self, event):
        if event.key == "enter":
            self.app.open_chat(self.employee_id)
            event.stop()


class DashboardScreen:
    """主面板"""
    pass  # 简化版，直接写在 App 中


class OpenClawFrontendApp(App):
    """TUI 前端主应用"""
    
    CSS_PATH = None  # 内联样式
    
    mouse_enabled = True
    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("r", "refresh", "刷新"),
    ]
    
    def __init__(self):
        super().__init__()
        self.client = BackendClient(BACKEND_API, BACKEND_WS)
        self.employees: List[Dict] = []
        self.selected_index = 0
        self._connected = False
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal(classes="toolbar"):
            yield Button("🔄 刷新", id="refresh", variant="primary")
            yield Button("← 返回", id="back", variant="default")
        
        with Vertical(classes="main-area"):
            yield Static("🦞 OpenClaw Studio - 连接后端服务...", id="title")
            with Vertical(id="employee-grid"):
                pass  # 动态加载
        
        with Horizontal(classes="status-bar"):
            yield Static("🟡 连接中...", id="connection-status")
            yield Static("🦞 0", id="employee-count")
        
        yield Footer()
    
    DEFAULT_CSS = """
    Screen { background: $surface; }
    Header { background: $primary-darken-3; }
    Footer { background: $primary-darken-3; }
    .toolbar { height: 3; background: $surface-darken-1; padding: 0 2; }
    .toolbar Button { margin-right: 1; }
    .main-area { height: 1fr; padding: 1; }
    #title { height: 3; text-style: bold; }
    #employee-grid { height: 1fr; }
    .status-bar { height: 1; background: $primary-darken-3; padding: 0 2; }
    EmployeeCard { margin: 0 1 1 0; }
    """
    
    async def on_mount(self):
        """挂载后连接后端"""
        # 注册事件回调
        self.client.on("init", self.on_init)
        self.client.on("employee_status_changed", self.on_status_changed)
        self.client.on("new_message", self.on_new_message)
        
        # 连接 WebSocket
        await self.client.connect_websocket()
        
        # 初始加载
        await self.load_employees()
    
    async def load_employees(self):
        """加载员工列表"""
        self.employees = await self.client.get_employees()
        self._connected = True
        self.update_display()
    
    def update_display(self):
        """更新显示"""
        # 更新标题
        title = self.query_one("#title", Static)
        title.update("🦞 OpenClaw Studio - 员工列表 (点击卡片进入对话)")
        
        # 更新状态栏
        status = self.query_one("#connection-status", Static)
        count = self.query_one("#employee-count", Static)
        
        if self._connected:
            status.update("🟢 已连接")
        else:
            status.update("🔴 断开")
        
        online = sum(1 for e in self.employees if e.get("status") != "offline")
        count.update(f"🦞 {online}/{len(self.employees)}")
        
        # 更新员工网格
        grid = self.query_one("#employee-grid", Vertical)
        grid.remove_children()
        
        row = Horizontal()
        for i, emp in enumerate(self.employees):
            if i > 0 and i % 3 == 0:
                grid.mount(row)
                row = Horizontal()
            card = EmployeeCard(emp)
            if i == self.selected_index:
                card.selected = True
            row.mount(card)
        
        if row.children:
            grid.mount(row)
    
    def on_init(self, employees: List[Dict]):
        """收到初始化数据"""
        self.employees = employees
        self._connected = True
        self.call_from_thread(self.update_display)
    
    def on_status_changed(self, data: Dict):
        """员工状态变化"""
        emp_id = data.get("employee_id")
        for emp in self.employees:
            if emp["id"] == emp_id:
                emp["status"] = data.get("status", emp["status"])
                emp["current_task"] = data.get("current_task", emp.get("current_task"))
                break
        self.call_from_thread(self.update_display)
    
    def on_new_message(self, data: Dict):
        """新消息"""
        emp_id = data.get("employee_id")
        for emp in self.employees:
            if emp["id"] == emp_id:
                emp["unread_count"] = emp.get("unread_count", 0) + 1
                break
        self.call_from_thread(self.update_display)
    
    def open_chat(self, employee_id: str):
        """打开聊天界面"""
        # 简化版：显示通知
        emp = next((e for e in self.employees if e["id"] == employee_id), None)
        if emp:
            self.notify(f"进入 {emp['name']} 的对话界面\n(完整版需要实现 ChatScreen)")
    
    async def on_button_pressed(self, event):
        """按钮点击"""
        if event.button.id == "refresh":
            await self.load_employees()
            self.notify("🔄 已刷新")
        elif event.button.id == "back":
            self.notify("← 返回")
    
    def action_refresh(self):
        """刷新快捷键"""
        asyncio.create_task(self.load_employees())


def main():
    """启动前端"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🦞 OpenClaw Frontend (TUI)                              ║
║                                                           ║
║   连接到后端: http://localhost:18765                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    app = OpenClawFrontendApp()
    app.run()


if __name__ == "__main__":
    main()
