#!/usr/bin/env python3
"""
🦞 OpenClaw TUI Studio - 交互式终端界面
支持键盘导航和鼠标操作
"""

import json
import asyncio
import uuid
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Callable
from datetime import datetime

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Static, Button, Input, Label, 
    ListView, ListItem, RichLog, TextArea
)
from textual.containers import Horizontal, Vertical, Container, Grid
from textual.reactive import reactive
from textual.binding import Binding
from textual import work

# ============ 数据模型 ============

@dataclass
class Employee:
    """OpenClaw 员工"""
    id: str
    name: str
    role: str = "OpenClaw 员工"
    status: str = "offline"  # offline, idle, working
    current_task: str = ""
    unread_count: int = 0
    avatar: str = "🦞"
    enabled: bool = True
    config: Dict = field(default_factory=dict)


class EmployeeStore:
    """员工数据管理"""
    
    def __init__(self):
        self.data_file = Path(__file__).parent / "data" / "employees.json"
        self.data_file.parent.mkdir(exist_ok=True)
        self.employees: Dict[str, Employee] = {}
        self.load()
    
    def load(self):
        """加载员工数据"""
        if self.data_file.exists():
            try:
                data = json.loads(self.data_file.read_text(encoding='utf-8'))
                for emp_id, emp_data in data.items():
                    self.employees[emp_id] = Employee(**emp_data)
            except Exception as e:
                print(f"加载数据失败: {e}")
        
        if not self.employees:
            self.create_defaults()
    
    def save(self):
        """保存员工数据"""
        data = {emp_id: asdict(emp) for emp_id, emp in self.employees.items()}
        self.data_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), 
            encoding='utf-8'
        )
    
    def create_defaults(self):
        """创建默认员工"""
        self.employees = {
            "emp-001": Employee(
                id="emp-001",
                name="Alice",
                role="代码审查专家",
                config={"base_url": "", "token": "", "session": "alice"}
            ),
            "emp-002": Employee(
                id="emp-002",
                name="Bob", 
                role="文档生成助手",
                config={"base_url": "", "token": "", "session": "bob"}
            ),
            "emp-003": Employee(
                id="emp-003",
                name="Carol",
                role="测试工程师",
                config={"base_url": "", "token": "", "session": "carol"}
            ),
        }
        self.save()
    
    def add(self, emp: Employee):
        """添加员工"""
        self.employees[emp.id] = emp
        self.save()
    
    def delete(self, emp_id: str):
        """删除员工"""
        if emp_id in self.employees:
            del self.employees[emp_id]
            self.save()
    
    def update(self, emp_id: str, **kwargs):
        """更新员工"""
        if emp_id in self.employees:
            emp = self.employees[emp_id]
            for key, value in kwargs.items():
                if hasattr(emp, key):
                    setattr(emp, key, value)
            self.save()


# ============ 组件 ============

class EmployeeCard(Container):
    """员工卡片组件"""
    
    DEFAULT_CSS = """
    EmployeeCard {
        width: 24;
        height: 11;
        background: $surface;
        border: solid $primary-darken-2;
        padding: 0;
        margin: 0 1 1 0;
    }
    EmployeeCard:hover {
        background: $surface-lighten-1;
        border: solid $primary;
    }
    EmployeeCard:focus {
        border: solid $accent;
        background: $primary-darken-3;
    }
    EmployeeCard.selected {
        border: solid $success;
        background: $success-darken-3;
    }
    EmployeeCard .header {
        height: 2;
        background: $primary-darken-3;
        content-align: center middle;
        text-style: bold;
    }
    EmployeeCard .body {
        height: 6;
        content-align: center middle;
    }
    EmployeeCard .avatar {
        text-style: bold;
        text-align: center;
    }
    EmployeeCard .name {
        text-style: bold;
        text-align: center;
        color: $text;
    }
    EmployeeCard .role {
        text-align: center;
        color: $text-muted;
        text-style: italic;
    }
    EmployeeCard .footer {
        height: 3;
        content-align: center middle;
        color: $text-muted;
    }
    EmployeeCard .status-idle { color: $success; }
    EmployeeCard .status-working { color: $warning; }
    EmployeeCard .status-offline { color: $error; }
    """
    
    def __init__(self, employee: Employee, **kwargs):
        super().__init__(**kwargs)
        self.employee = employee
        self.can_focus = True
    
    def compose(self):
        emp = self.employee
        
        # 状态指示
        status_emoji = {"idle": "🟢", "working": "🟡", "offline": "⚫"}.get(emp.status, "⚪")
        status_text = {"idle": "空闲", "working": "工作中", "offline": "离线"}.get(emp.status, "未知")
        
        # 头部：状态 + 未读消息
        header_text = f"{status_emoji} {status_text}"
        if emp.unread_count > 0:
            header_text += f"  💬{emp.unread_count}"
        
        yield Static(header_text, classes=f"header status-{emp.status}")
        
        # 主体：头像 + 姓名 + 角色
        with Vertical(classes="body"):
            yield Static(emp.avatar, classes="avatar")
            yield Static(emp.name, classes="name")
            yield Static(emp.role, classes="role")
        
        # 底部：当前任务
        task = emp.current_task or "无任务"
        if len(task) > 12:
            task = task[:12] + "..."
        yield Static(f"📋 {task}", classes="footer")
    
    def on_click(self):
        """鼠标点击"""
        self.app.select_employee(self.employee)
    
    def on_key(self, event):
        """键盘事件"""
        if event.key == "enter":
            self.app.enter_chat(self.employee)
        elif event.key == "space":
            self.app.show_employee_menu(self.employee)


class EmployeeDetailModal(Container):
    """员工详情弹窗"""
    
    DEFAULT_CSS = """
    EmployeeDetailModal {
        width: 60;
        height: auto;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
    }
    EmployeeDetailModal .title {
        text-style: bold;
        text-align: center;
        height: 3;
        border-bottom: solid $primary-darken-2;
    }
    EmployeeDetailModal .info-row {
        height: 2;
        margin: 1 0;
    }
    EmployeeDetailModal .label {
        color: $text-muted;
        width: 15;
    }
    EmployeeDetailModal .value {
        color: $text;
    }
    EmployeeDetailModal .buttons {
        height: 3;
        margin-top: 1;
        align: center middle;
    }
    EmployeeDetailModal .buttons Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, employee: Employee, **kwargs):
        super().__init__(**kwargs)
        self.employee = employee
    
    def compose(self):
        emp = self.employee
        
        yield Static(f"🦞 {emp.name} - 员工详情", classes="title")
        
        with Grid(classes="info-grid"):
            yield Label("ID:", classes="label"); yield Label(emp.id, classes="value")
            yield Label("姓名:", classes="label"); yield Label(emp.name, classes="value")
            yield Label("角色:", classes="label"); yield Label(emp.role, classes="value")
            yield Label("状态:", classes="label"); yield Label(emp.status, classes="value")
            yield Label("当前任务:", classes="label"); yield Label(emp.current_task or "无", classes="value")
            yield Label("未读消息:", classes="label"); yield Label(str(emp.unread_count), classes="value")
        
        with Horizontal(classes="buttons"):
            yield Button("💬 对话", id="chat", variant="primary")
            yield Button("✏️ 编辑", id="edit", variant="default")
            yield Button("🗑️ 删除", id="delete", variant="error")
            yield Button("← 返回", id="back", variant="default")
    
    def on_button_pressed(self, event):
        btn_id = event.button.id
        if btn_id == "chat":
            self.app.enter_chat(self.employee)
        elif btn_id == "edit":
            self.app.edit_employee(self.employee)
        elif btn_id == "delete":
            self.app.delete_employee(self.employee)
        elif btn_id == "back":
            self.app.dismiss_modal()


# ============ 屏幕 ============

class StudioScreen(Screen):
    """工作室主界面"""
    
    BINDINGS = [
        Binding("up", "nav_up", "上", show=False),
        Binding("down", "nav_down", "下", show=False),
        Binding("left", "nav_left", "左", show=False),
        Binding("right", "nav_right", "右", show=False),
        Binding("enter", "action_enter", "确认", show=False),
        Binding("escape", "action_back", "返回", show=False),
        Binding("q", "action_quit", "退出", show=True),
        Binding("a", "action_add", "添加员工", show=True),
        Binding("?", "action_help", "帮助", show=True),
    ]
    
    employees = reactive(list)
    selected_index = reactive(0)
    
    def __init__(self, store: EmployeeStore, **kwargs):
        super().__init__(**kwargs)
        self.store = store
        self.employees = list(store.employees.values())
        self.cards: List[EmployeeCard] = []
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Vertical():
            # 工具栏
            with Horizontal(classes="toolbar"):
                yield Button("➕ 添加员工", id="add-btn", variant="success")
                yield Button("🔄 刷新", id="refresh-btn", variant="primary")
                yield Button("❓ 帮助", id="help-btn", variant="default")
                yield Static("", classes="spacer")
                yield Static("🦞 OpenClaw Studio", classes="brand")
            
            # 标题提示
            yield Static(
                "↑↓←→ 导航 │ Enter 进入对话 │ Space 菜单 │ 鼠标点击选择",
                classes="hint"
            )
            
            # 员工网格
            with Grid(id="employee-grid", classes="grid"):
                for emp in self.employees:
                    card = EmployeeCard(emp)
                    self.cards.append(card)
                    yield card
            
            # 状态栏
            with Horizontal(classes="statusbar"):
                yield Static("🟢 就绪", id="status")
                yield Static("", classes="spacer")
                total = len(self.employees)
                online = sum(1 for e in self.employees if e.status != "offline")
                yield Static(f"🦞 {online}/{total} 在线", id="stats")
        
        yield Footer()
    
    DEFAULT_CSS = """
    StudioScreen .toolbar {
        height: 3;
        background: $surface-darken-1;
        padding: 0 2;
        align: left middle;
    }
    StudioScreen .toolbar Button {
        margin-right: 1;
    }
    StudioScreen .toolbar .spacer {
        width: 1fr;
    }
    StudioScreen .toolbar .brand {
        text-style: bold;
        color: $accent;
    }
    StudioScreen .hint {
        height: 1;
        padding: 0 2;
        color: $text-muted;
        text-style: dim;
        text-align: center;
    }
    StudioScreen .grid {
        height: 1fr;
        padding: 1 2;
        grid-size: 4;
        grid-columns: 1fr 1fr 1fr 1fr;
        grid-gutter: 1;
    }
    StudioScreen .statusbar {
        height: 1;
        background: $primary-darken-3;
        padding: 0 2;
        align: left middle;
    }
    StudioScreen .statusbar .spacer {
        width: 1fr;
    }
    """
    
    def on_mount(self):
        """挂载后聚焦第一个卡片"""
        if self.cards:
            self.cards[0].focus()
    
    def action_nav_up(self):
        """向上导航"""
        self.move_selection(-4)  # 每行4个
    
    def action_nav_down(self):
        """向下导航"""
        self.move_selection(4)
    
    def action_nav_left(self):
        """向左导航"""
        self.move_selection(-1)
    
    def action_nav_right(self):
        """向右导航"""
        self.move_selection(1)
    
    def move_selection(self, delta: int):
        """移动选择"""
        if not self.cards:
            return
        
        new_index = self.selected_index + delta
        new_index = max(0, min(new_index, len(self.cards) - 1))
        
        if new_index != self.selected_index:
            self.selected_index = new_index
            self.cards[new_index].focus()
    
    def action_enter(self):
        """确认键 - 进入对话"""
        if self.cards and 0 <= self.selected_index < len(self.cards):
            emp = self.cards[self.selected_index].employee
            self.app.enter_chat(emp)
    
    def action_back(self):
        """返回键"""
        self.app.action_quit()
    
    def action_quit(self):
        """退出"""
        self.app.exit()
    
    def action_add(self):
        """添加员工"""
        self.app.push_screen(AddEmployeeScreen(self.store))
    
    def action_help(self):
        """显示帮助"""
        help_text = """
📖 操作指南

🖱️ 鼠标:
  点击卡片     选中员工
  双击卡片     进入对话

⌨️ 键盘:
  ↑↓←→         导航选择
  Enter        进入对话
  Space        打开菜单
  a            添加员工
  q            退出

📊 图标说明:
  🦞 员工      💬 未读消息
  🟢 空闲      🟡 工作中
  ⚫ 离线      📋 当前任务
"""
        self.notify(help_text, title="帮助", timeout=15)
    
    def on_button_pressed(self, event):
        """按钮点击"""
        btn_id = event.button.id
        if btn_id == "add-btn":
            self.action_add()
        elif btn_id == "refresh-btn":
            self.refresh_employees()
        elif btn_id == "help-btn":
            self.action_help()
    
    def refresh_employees(self):
        """刷新员工列表"""
        self.store.load()
        self.employees = list(self.store.employees.values())
        
        # 重新渲染
        grid = self.query_one("#employee-grid", Grid)
        grid.remove_children()
        self.cards = []
        
        for emp in self.employees:
            card = EmployeeCard(emp)
            self.cards.append(card)
            grid.mount(card)
        
        # 更新状态
        total = len(self.employees)
        online = sum(1 for e in self.employees if e.status != "offline")
        self.query_one("#stats", Static).update(f"🦞 {online}/{total} 在线")
        
        self.notify("🔄 已刷新", timeout=2)


class ChatScreen(Screen):
    """对话界面"""
    
    BINDINGS = [
        Binding("escape", "action_back", "返回", show=True),
        Binding("enter", "action_send", "发送", show=False),
    ]
    
    def __init__(self, employee: Employee, store: EmployeeStore, **kwargs):
        super().__init__(**kwargs)
        self.employee = employee
        self.store = store
        self.messages: List[Dict] = []
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Vertical():
            # 聊天头部
            with Horizontal(classes="chat-header"):
                yield Button("← 返回工作室", id="back-btn", variant="default")
                yield Static(f"🦞 {self.employee.name} ({self.employee.role})", classes="chat-title")
            
            # 消息区域
            yield RichLog(id="messages", classes="messages", wrap=True)
            
            # 输入区域
            with Horizontal(classes="input-area"):
                yield Input(
                    placeholder="💭 输入消息，Enter 发送...",
                    id="message-input"
                )
                yield Button("📤 发送", id="send-btn", variant="primary")
        
        yield Footer()
    
    DEFAULT_CSS = """
    ChatScreen .chat-header {
        height: 3;
        background: $primary-darken-3;
        padding: 0 2;
        align: left middle;
    }
    ChatScreen .chat-title {
        margin-left: 2;
        text-style: bold;
    }
    ChatScreen .messages {
        height: 1fr;
        background: $surface-darken-1;
        padding: 1 2;
        border-bottom: solid $primary-darken-2;
    }
    ChatScreen .input-area {
        height: 3;
        padding: 0 2;
        align: left middle;
    }
    ChatScreen .input-area Input {
        width: 1fr;
    }
    ChatScreen .input-area Button {
        margin-left: 1;
    }
    """
    
    def on_mount(self):
        """挂载后"""
        self.add_message("system", f"🦞 与 {self.employee.name} 的对话已开始")
        self.add_message("system", "💡 提示: 输入消息按 Enter 发送，Esc 返回工作室")
        self.query_one("#message-input", Input).focus()
    
    def add_message(self, sender: str, content: str):
        """添加消息"""
        log = self.query_one("#messages", RichLog)
        timestamp = datetime.now().strftime("%H:%M")
        
        if sender == "system":
            log.write(f"[{timestamp}] 💬 {content}")
        elif sender == "user":
            log.write(f"[{timestamp}] 🧑 你: {content}")
        else:
            log.write(f"[{timestamp}] 🦞 {self.employee.name}: {content}")
        
        log.write("")
    
    def on_button_pressed(self, event):
        """按钮点击"""
        if event.button.id == "back-btn":
            self.action_back()
        elif event.button.id == "send-btn":
            self.action_send()
    
    def on_input_submitted(self, event):
        """输入提交"""
        if event.input.id == "message-input":
            self.action_send()
    
    def action_send(self):
        """发送消息"""
        input_widget = self.query_one("#message-input", Input)
        content = input_widget.value.strip()
        
        if not content:
            return
        
        input_widget.value = ""
        self.add_message("user", content)
        
        # 模拟回复（实际应发送到 OpenClaw）
        self.add_message("employee", f"收到: {content[:20]}...")
    
    def action_back(self):
        """返回"""
        self.app.pop_screen()


class AddEmployeeScreen(Screen):
    """添加员工界面"""
    
    BINDINGS = [
        Binding("escape", "action_back", "返回", show=True),
    ]
    
    def __init__(self, store: EmployeeStore, **kwargs):
        super().__init__(**kwargs)
        self.store = store
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Container(classes="form-container"):
            yield Static("➕ 添加新员工", classes="form-title")
            
            with Vertical(classes="form"):
                yield Label("基本信息")
                yield Input(placeholder="员工名称 *", id="name")
                yield Input(placeholder="角色（如：代码审查专家）", id="role", value="OpenClaw 员工")
                
                yield Label("OpenClaw 配置 (可选)")
                yield Input(placeholder="Gateway URL", id="base_url")
                yield Input(placeholder="Token", id="token", password=True)
                
                with Horizontal(classes="form-buttons"):
                    yield Button("← 返回", id="back-btn", variant="default")
                    yield Button("✅ 创建", id="create-btn", variant="success")
        
        yield Footer()
    
    DEFAULT_CSS = """
    AddEmployeeScreen .form-container {
        width: 60;
        height: auto;
        margin: 2 auto;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    AddEmployeeScreen .form-title {
        text-style: bold;
        text-align: center;
        height: 3;
        border-bottom: solid $primary-darken-2;
    }
    AddEmployeeScreen .form {
        padding: 1 0;
    }
    AddEmployeeScreen .form Label {
        margin-top: 1;
        color: $text-muted;
    }
    AddEmployeeScreen .form Input {
        margin: 0 0 1 0;
    }
    AddEmployeeScreen .form-buttons {
        height: 3;
        margin-top: 1;
        align: center middle;
    }
    AddEmployeeScreen .form-buttons Button {
        margin: 0 1;
    }
    """
    
    def on_button_pressed(self, event):
        """按钮点击"""
        btn_id = event.button.id
        if btn_id == "back-btn":
            self.action_back()
        elif btn_id == "create-btn":
            self.create_employee()
    
    def create_employee(self):
        """创建员工"""
        name = self.query_one("#name", Input).value.strip()
        role = self.query_one("#role", Input).value.strip()
        base_url = self.query_one("#base_url", Input).value.strip()
        token = self.query_one("#token", Input).value.strip()
        
        if not name:
            self.notify("❌ 请输入员工名称", severity="error", timeout=3)
            return
        
        emp_id = f"emp-{uuid.uuid4().hex[:6]}"
        emp = Employee(
            id=emp_id,
            name=name,
            role=role,
            config={"base_url": base_url, "token": token, "session": name.lower()}
        )
        
        self.store.add(emp)
        self.notify(f"✅ 员工 '{name}' 创建成功!", timeout=3)
        self.app.pop_screen()
        
        # 刷新工作室界面
        if isinstance(self.app.screen, StudioScreen):
            self.app.screen.refresh_employees()
    
    def action_back(self):
        """返回"""
        self.app.pop_screen()


# ============ 主应用 ============

class OpenClawStudioApp(App):
    """OpenClaw Studio 主应用"""
    
    CSS_PATH = None
    mouse_enabled = True
    
    def __init__(self):
        super().__init__()
        self.store = EmployeeStore()
    
    def compose(self) -> ComposeResult:
        yield StudioScreen(self.store)
    
    def select_employee(self, employee: Employee):
        """选中员工"""
        # 更新选中状态
        screen = self.screen
        if isinstance(screen, StudioScreen):
            for i, card in enumerate(screen.cards):
                if card.employee.id == employee.id:
                    screen.selected_index = i
                    card.focus()
                    break
    
    def enter_chat(self, employee: Employee):
        """进入对话"""
        self.push_screen(ChatScreen(employee, self.store))
    
    def show_employee_menu(self, employee: Employee):
        """显示员工菜单"""
        # 简单实现：直接显示详情弹窗
        self.notify(
            f"🦞 {employee.name}\n"
            f"角色: {employee.role}\n"
            f"状态: {employee.status}\n"
            f"任务: {employee.current_task or '无'}\n\n"
            f"按 Enter 进入对话",
            title="员工详情",
            timeout=5
        )
    
    def edit_employee(self, employee: Employee):
        """编辑员工"""
        self.notify("✏️ 编辑功能开发中...", timeout=2)
    
    def delete_employee(self, employee: Employee):
        """删除员工"""
        self.store.delete(employee.id)
        self.notify(f"🗑️ 员工 '{employee.name}' 已删除", timeout=3)
        
        # 刷新界面
        screen = self.screen
        if isinstance(screen, StudioScreen):
            screen.refresh_employees()
    
    def dismiss_modal(self):
        """关闭弹窗"""
        pass  # 简单实现


def main():
    """入口"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🦞 OpenClaw TUI Studio                                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # 检查依赖
    try:
        import textual
    except ImportError:
        print("❌ 缺少依赖，请运行: pip3 install textual")
        return 1
    
    app = OpenClawStudioApp()
    app.run()
    return 0


if __name__ == "__main__":
    exit(main())
