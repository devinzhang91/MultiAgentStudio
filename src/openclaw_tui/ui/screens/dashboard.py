"""主面板屏幕 - 支持键盘导航"""
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive

from ..widgets.employee_list import EmployeeList
from ..widgets.status_bar import StatusBar


class DashboardScreen(Screen):
    """主面板 - OpenClaw 工作室总览，支持键盘导航"""
    
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
        min-width: 10;
    }
    DashboardScreen .toolbar Button:focus {
        background: $accent;
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
        padding: 0 2;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("r", "action_refresh", "刷新"),
        ("?", "show_help", "帮助"),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.employees = [
            {"id": "alice-001", "name": "Alice", "role": "代码审查专家", "status": "idle", "current_task": "", "unread": 0},
            {"id": "bob-002", "name": "Bob", "role": "文档生成助手", "status": "working", "current_task": "生成 API 文档", "unread": 2},
            {"id": "carol-003", "name": "Carol", "role": "测试工程师", "status": "idle", "current_task": "", "unread": 0},
            {"id": "dave-004", "name": "Dave", "role": "DevOps 专家", "status": "offline", "current_task": "", "unread": 0},
            {"id": "eve-005", "name": "Eve", "role": "数据分析助手", "status": "working", "current_task": "分析日志数据", "unread": 1},
        ]
    
    def compose(self):
        """组装主面板"""
        yield Header(show_clock=True)
        
        # 工具栏 - 按钮可以 Tab 导航
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
            self.action_refresh()
        elif event.button.id == "settings-btn":
            self.notify("⚙️ 设置功能开发中...", severity="information")
        elif event.button.id == "help-btn":
            self.action_show_help()
    
    def action_refresh(self):
        """刷新数据"""
        self.notify("🔄 正在刷新...", severity="information")
        # 刷新员工列表
        emp_list = self.query_one(EmployeeList)
        # 模拟数据更新
        for emp in self.employees:
            if emp["id"] == "alice-001":
                emp["status"] = "working"
                emp["current_task"] = "代码审查中..."
                break
        emp_list.employees = self.employees
    
    def action_show_help(self):
        """显示帮助信息"""
        help_text = """
📖 键盘操作指南

导航:
  ↑/↓/←/→   在员工卡片间移动
  Tab       在按钮和卡片间切换
  Home      跳到第一个员工
  End       跳到最后一个员工

操作:
  Enter     进入对话 / 点击按钮
  Space     查看员工详情
  q         退出应用
  r         刷新数据
  ?         显示帮助

图标说明:
  🦞  OpenClaw 员工    💬  未读消息
  🟢  空闲状态         🟡  工作中
  ⚫  离线状态         📋  当前任务
        """
        self.notify(help_text, severity="information", timeout=15)
