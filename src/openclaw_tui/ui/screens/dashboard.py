"""主面板屏幕"""
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive

from ..widgets.employee_list import EmployeeList
from ..widgets.status_bar import StatusBar


class DashboardScreen(Screen):
    """主面板 - 展示所有员工总览"""
    
    employees = reactive(list)
    
    DEFAULT_CSS = """
    DashboardScreen {
        layout: grid;
        grid-size: 2;
        grid-columns: 15 1fr;
    }
    DashboardScreen .sidebar {
        width: 100%;
        height: 100%;
        border-right: solid $primary;
        background: $surface-darken-1;
        padding: 1;
    }
    DashboardScreen .sidebar .nav-item {
        height: 3;
        content-align: left middle;
        padding: 0 1;
        margin: 1 0;
    }
    DashboardScreen .sidebar .nav-item:hover {
        background: $primary-darken-2;
    }
    DashboardScreen .main-content {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    DashboardScreen .title-bar {
        height: 3;
        content-align: left middle;
        text-style: bold;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 默认员工数据
        self.employees = [
            {
                "id": "alice-001",
                "name": "Alice",
                "role": "代码审查专家",
                "avatar": "👩‍💻",
                "status": "idle",
                "current_task": ""
            },
            {
                "id": "bob-002",
                "name": "Bob",
                "role": "文档生成助手",
                "avatar": "👨‍💻",
                "status": "working",
                "current_task": "生成 API 文档..."
            },
            {
                "id": "carol-003",
                "name": "Carol",
                "role": "测试工程师",
                "avatar": "🧪",
                "status": "idle",
                "current_task": ""
            },
            {
                "id": "dave-004",
                "name": "Dave",
                "role": "DevOps 专家",
                "avatar": "👾",
                "status": "offline",
                "current_task": ""
            },
            {
                "id": "eve-005",
                "name": "Eve",
                "role": "数据分析助手",
                "avatar": "🤖",
                "status": "working",
                "current_task": "等待输入..."
            }
        ]
    
    def compose(self):
        """组装主面板"""
        yield Header(show_clock=True)
        
        # 侧边栏
        with Vertical(classes="sidebar"):
            yield Static("👥 员工\n────", classes="nav-item")
            yield Static("📊 统计\n────", classes="nav-item")
            yield Static("💬 消息\n────", classes="nav-item")
            yield Static("")
            yield Button("刷新", id="refresh-btn", variant="primary")
            yield Button("设置", id="settings-btn", variant="default")
        
        # 主内容区
        with Vertical(classes="main-content"):
            yield Static("🎮 OpenClaw TUI Studio - AI 员工管理面板", classes="title-bar")
            yield EmployeeList(employees=self.employees)
        
        yield StatusBar(id="status-bar")
        yield Footer()
    
    def on_mount(self):
        """挂载时更新状态栏"""
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.total_count = len(self.employees)
        status_bar.online_count = sum(1 for e in self.employees if e["status"] != "offline")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "refresh-btn":
            self.refresh_data()
        elif event.button.id == "settings-btn":
            self.app.push_screen("settings")
    
    def refresh_data(self):
        """刷新数据"""
        # TODO: 从 OpenClaw API 获取最新数据
        self.notify("正在刷新数据...", severity="information")
