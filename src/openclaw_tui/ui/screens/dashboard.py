"""主面板屏幕 - 平面工作室风格"""
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive

from ..widgets.employee_list import EmployeeList
from ..widgets.status_bar import StatusBar


class DashboardScreen(Screen):
    """主面板 - OpenClaw 工作室总览"""
    
    employees = reactive(list)
    
    DEFAULT_CSS = """
    DashboardScreen {
        layout: vertical;
    }
    DashboardScreen .toolbar {
        height: 3;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-2;
        padding: 0 2;
        content-align: left middle;
    }
    DashboardScreen .toolbar Button {
        margin-right: 1;
    }
    DashboardScreen .main-area {
        height: 1fr;
        padding: 1;
    }
    DashboardScreen .title-section {
        height: 3;
        content-align: left middle;
        text-style: bold;
        margin-bottom: 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 默认员工数据 - 使用🦞作为图标
        self.employees = [
            {
                "id": "alice-001",
                "name": "Alice",
                "role": "代码审查专家",
                "status": "idle",
                "current_task": "",
                "unread": 0,
            },
            {
                "id": "bob-002",
                "name": "Bob",
                "role": "文档生成助手",
                "status": "working",
                "current_task": "生成 API 文档",
                "unread": 2,
            },
            {
                "id": "carol-003",
                "name": "Carol",
                "role": "测试工程师",
                "status": "idle",
                "current_task": "",
                "unread": 0,
            },
            {
                "id": "dave-004",
                "name": "Dave",
                "role": "DevOps 专家",
                "status": "offline",
                "current_task": "",
                "unread": 0,
            },
            {
                "id": "eve-005",
                "name": "Eve",
                "role": "数据分析助手",
                "status": "working",
                "current_task": "分析日志数据",
                "unread": 1,
            },
        ]
    
    def compose(self):
        """组装主面板"""
        yield Header(show_clock=True)
        
        # 工具栏
        with Horizontal(classes="toolbar"):
            yield Button("🔄 刷新", id="refresh-btn", variant="primary")
            yield Button("⚙️ 设置", id="settings-btn", variant="default")
            yield Button("❓ 帮助", id="help-btn", variant="default")
        
        # 主内容区
        with Vertical(classes="main-area"):
            yield Static("🦞 OpenClaw 工作室 - 员工列表", classes="title-section")
            yield EmployeeList(employees=self.employees)
        
        yield StatusBar(id="status-bar")
        yield Footer()
    
    def on_mount(self):
        """挂载时更新状态栏"""
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.total_count = len(self.employees)
        status_bar.online_count = sum(1 for e in self.employees if e["status"] != "offline")
        status_bar.unread_total = sum(e.get("unread", 0) for e in self.employees)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "refresh-btn":
            self.refresh_data()
        elif event.button.id == "settings-btn":
            self.notify("设置功能开发中...", severity="information")
        elif event.button.id == "help-btn":
            self.show_help()
    
    def refresh_data(self):
        """刷新数据"""
        self.notify("🔄 正在刷新...", severity="information")
        # TODO: 从 OpenClaw API 获取最新数据
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
📖 快捷键说明:

  q      - 退出应用
  r      - 刷新数据  
  ↑/↓    - 导航
  Enter  - 打开对话
  
🦞 员工状态:
  🟢 空闲  │  🟡 工作中  │  ⚫ 离线
  
💬 未读消息会在卡片上显示
        """
        self.notify(help_text, severity="information", timeout=10)
