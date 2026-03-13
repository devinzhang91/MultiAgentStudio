#!/usr/bin/env python3
"""
🦞 MushTech TUI Studio - 纯键盘极客风格
"""

import unicodedata
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Static, Input, Button
from textual.containers import Vertical, Grid, Horizontal
from textual.reactive import reactive
from textual import work
from rich.text import Text

from .models import EmployeeStore, Employee
from .chat_screen import ChatScreen
from .agent_management_screen import AgentManagementScreen
from .message_manager import get_message_manager, MessageManager
from .logger import logger


class MushTechStudioApp(App):
    """MushTech Studio - Keyboard Only"""
    
    CSS = """
    .main-container {
        width: 100%;
        height: 100%;
        background: black;
    }
    
    .toolbar { 
        height: 1; 
        background: black;
        color: green;
    }
    
    /* 员工列表样式 - 列显示 */
    .employee-list {
        width: 100%;
        height: 1fr;
        background: black;
        padding: 0 1;
        overflow-y: auto;
    }
    
    /* 表头 */
    .employee-header {
        height: auto;
        background: black;
        color: green;
        text-style: bold;
        border-bottom: solid green;
        padding: 0 0 1 0;
    }
    
    /* 员工行 */
    .employee-row {
        height: auto;
        min-height: 1;
        background: black;
        color: green;
        border-bottom: solid darkgreen;
        padding: 0 0 1 0;
    }
    
    .employee-row:focus {
        background: darkgreen;
        color: black;
        text-style: bold;
    }
    
    /* 状态颜色 */
    .employee-row-disconnected { color: gray; }
    .employee-row-connecting { color: yellow; }
    .employee-row-connected { color: ansi_bright_green; }
    .employee-row-working { color: cyan; }
    .employee-row-error { color: red; }
    .employee-row-idle { color: white; }
    .employee-row-unread { color: cyan; text-style: bold; }
    
    .statusbar { 
        height: 1; 
        background: black;
        color: green;
    }
    
    .dialog {
        width: 60;
        height: auto;
        background: black;
        border: solid green;
        padding: 1 2;
    }
    
    .dialog-title {
        text-align: center;
        text-style: bold;
        color: green;
    }
    
    .dialog-message {
        text-align: center;
        margin: 1 0;
    }
    
    .dialog-buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }
    
    .dialog-btn {
        width: 12;
        margin: 0 1;
        background: black;
        color: green;
        border: solid green;
    }
    
    .help-text {
        color: green;
        text-style: dim;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("r", "refresh", "刷新"),
        ("m", "manage_agents", "管理"),
        ("?", "help", "帮助"),
    ]
    
    # 列宽定义（显示宽度）
    COL_EMOJI = 4    #  表情 + 空格 
    COL_NAME = 16    # 姓名
    COL_ROLE = 28    # 职位
    COL_STATUS = 12   # 状态
    COL_MESSAGE = 42  # 最新消息
    
    def __init__(self):
        super().__init__()
        self.store = EmployeeStore()
        self.msg_manager = get_message_manager(self.store)
        self.cards = []
        self.employee_list = []
        self.selected_index = 0
        
        # 注册消息管理器回调
        self.msg_manager.on_message_received = self._on_message_received
        self.msg_manager.on_unread_changed = self._on_unread_changed
        self.msg_manager.on_status_changed = self._on_status_changed
    
    def compose(self) -> ComposeResult:
        """构建主界面"""
        logger.info("Composing main UI...")
        
        with Vertical(classes="main-container"):
            # 标题栏
            yield Static(
                " 🦞  MushTech TUI Studio  -  多智能体管理界面  |  纯键盘操作",
                classes="toolbar"
            )
            
            # 员工列表
            with Vertical(classes="employee-list"):
                # 表头
                header = self._format_row(" 👤 ", "NAME", "ROLE", "STATUS", "MESSAGE", is_header=True)
                yield Static(header, classes="employee-header")
                
                # 员工行
                self.employee_list = sorted(self.store.employees.values(), key=lambda e: e.id)
                logger.info(f"Creating {len(self.employee_list)} employee rows")
                for emp in self.employee_list:
                    item = self._create_employee_row(emp)
                    self.cards.append(item)
                    yield item
            
            # 状态栏
            with Horizontal(classes="statusbar"):
                total = len(self.store.employees)
                enabled = sum(1 for e in self.store.employees.values() if e.enabled)
                yield Static(f" [OK] {total} agents | {enabled} enabled | MONITOR", id="status-text")
        
        yield Footer()
    
    @staticmethod
    def _display_width(s: str) -> int:
        """计算字符串的显示宽度（处理中文和emoji）"""
        width = 0
        for char in s:
            if unicodedata.east_asian_width(char) in ('F', 'W'):
                width += 2
            elif unicodedata.category(char) == 'So':
                width += 2
            else:
                width += 1
        return width
    
    @classmethod
    def _pad_to_width(cls, s: str, width: int) -> str:
        """将字符串填充到指定显示宽度"""
        current_width = cls._display_width(s)
        padding = width - current_width
        if padding > 0:
            return s + ' ' * padding
        elif padding < 0:
            result = ''
            w = 0
            for char in s:
                char_width = cls._display_width(char)
                if w + char_width > width - 1:
                    return result + '…'
                result += char
                w += char_width
            return result + ' ' * (width - w)
        return s
    
    def _format_row(self, emoji: str, name: str, role: str, status: str, message: str, is_header: bool = False) -> str:
        """格式化行内容，确保所有列对齐"""
        emoji_col = self._pad_to_width(emoji, self.COL_EMOJI)
        name_col = self._pad_to_width(name, self.COL_NAME)
        role_col = self._pad_to_width(role, self.COL_ROLE)
        status_col = self._pad_to_width(status, self.COL_STATUS)
        message_col = self._pad_to_width(message, self.COL_MESSAGE)
        return f"{emoji_col}{name_col} {role_col} {status_col} {message_col}"

    def _latest_message_preview(self, emp_id: str) -> str:
        """获取主界面用于监控的最新消息预览。"""
        messages = self.msg_manager.get_messages(emp_id)
        if not messages:
            return "-"

        for msg in reversed(messages):
            if msg.sender in {"__thinking__", "system"}:
                continue
            text = (msg.content or "").replace("\n", " ").strip()
            if text:
                return text

        # 如果没有普通消息，回退到最后一条可见消息
        fallback = (messages[-1].content or "").replace("\n", " ").strip()
        return fallback or "-"
    
    def _get_status_text(self, status: str) -> str:
        """获取状态文本（统一宽度为6个字符显示宽度）"""
        # 统一格式: emoji + 两个中文字符，不足用空格补齐
        status_map = {
            "connected": "🟢 在线 ",   # 2+1+4=7 -> 加空格=8? 不对，重新计算
            "disconnected": "⚫ 离线 ",
            "connecting": "🟡 连接中",  # 2+1+6=9
            "working": "🔵 工作中",     # 2+1+6=9
            "error": "🔴 错误 ",
            "idle": "⚪ 空闲 ",
        }
        text = status_map.get(status, "⚫ 离线 ")
        # 统一填充到显示宽度 10
        return self._pad_to_width(text, self.COL_STATUS)
    
    def _create_employee_row(self, emp: Employee) -> Static:
        """创建员工行"""
        status = self.msg_manager.get_status(emp.id)
        
        # 监控视图按状态着色
        row_class = f"employee-row employee-row-{status}"
        
        # 格式化各列
        emoji_col = f" {emp.emoji} "
        message_preview = self._latest_message_preview(emp.id)
        
        content = self._format_row(
            emoji_col,
            emp.name,
            emp.role,
            self._get_status_text(status),
            message_preview
        )
        
        row = Static(Text(content), classes=row_class)
        row.can_focus = True
        row.employee_id = emp.id
        return row
    
    def on_mount(self):
        """初始化 - 启动时连接所有员工"""
        logger.info("App mounted")
        if self.cards:
            self.selected_index = 0
            self.cards[0].focus()
        
        # 启动时连接所有员工（保持现有行为）
        self.run_worker(self._connect_all())
    
    async def _connect_all(self):
        """连接所有员工"""
        logger.info("Connecting all employees...")
        await self.msg_manager.connect_all()
        self._refresh_grid()
    
    def _on_message_received(self, emp_id: str, sender: str, content: str):
        """收到消息回调"""
        try:
            self.app.call_from_thread(self._update_card, emp_id)
        except Exception:
            pass
    
    def _on_unread_changed(self, emp_id: str, unread_count: int):
        """未读数变化回调"""
        try:
            self.app.call_from_thread(self._update_card, emp_id)
            self.app.call_from_thread(self._update_status_bar)
        except Exception:
            pass
    
    def _on_status_changed(self, emp_id: str, status: str):
        """状态变化回调"""
        try:
            self.app.call_from_thread(self._update_card, emp_id)
        except Exception:
            pass
    
    def _update_card(self, emp_id: str):
        """更新单个员工行 - 使用相同的格式化逻辑"""
        try:
            for i, emp in enumerate(self.employee_list):
                if emp.id == emp_id and i < len(self.cards):
                    row = self.cards[i]
                    had_focus = row.has_focus
                    
                    # 获取最新数据
                    status = self.msg_manager.get_status(emp.id)
                    
                    # 监控视图按状态着色
                    row_class = f"employee-row employee-row-{status}"
                    row.classes = row_class
                    
                    # 使用相同的格式化方法更新内容
                    emoji_col = f" {emp.emoji} "
                    message_preview = self._latest_message_preview(emp.id)
                    
                    content = self._format_row(
                        emoji_col,
                        emp.name,
                        emp.role,
                        self._get_status_text(status),
                        message_preview
                    )
                    row.update(Text(content))
                    
                    if had_focus:
                        row.focus()
                    break
        except Exception as e:
            logger.error(f"Failed to update card for {emp_id}: {e}")
    
    def _update_status_bar(self):
        """更新状态栏"""
        try:
            status = self.query_one("#status-text", Static)
            total = len(self.store.employees)
            enabled = sum(1 for e in self.store.employees.values() if e.enabled)
            status.update(f" [OK] {total} agents | {enabled} enabled | MONITOR")
        except Exception as e:
            logger.error(f"Failed to update status bar: {e}")
    
    def _refresh_grid(self):
        """刷新整个网格"""
        try:
            for emp in self.employee_list:
                self._update_card(emp.id)
        except Exception as e:
            logger.error(f"Failed to refresh grid: {e}")
    
    def on_key(self, event):
        """键盘导航"""
        try:
            screen_stack = self.app.get_screen_stack()
            if len(screen_stack) > 1:
                return
        except Exception:
            pass
        
        if event.key == "up":
            self._move_selection(-1)
        elif event.key == "down":
            self._move_selection(1)
        elif event.key == "enter":
            self._open_chat()
    
    def _get_focused_index(self) -> int:
        """获取当前聚焦的索引"""
        for i, card in enumerate(self.cards):
            if card.has_focus:
                return i
        return self.selected_index if self.cards else -1
    
    def _move_selection(self, delta: int):
        """移动选择"""
        if not self.cards:
            return
        
        current = self._get_focused_index()
        new_index = max(0, min(current + delta, len(self.cards) - 1))
        self.selected_index = new_index
        self.cards[new_index].focus()
    
    def _open_chat(self):
        """打开聊天界面"""
        idx = self._get_focused_index()
        if idx < 0 or idx >= len(self.employee_list):
            return
        
        emp = self.employee_list[idx]
        logger.info(f"Opening chat for {emp.id}")
        
        # 切换到聊天界面
        self.push_screen(ChatScreen(emp, self.msg_manager))
    
    def action_refresh(self):
        """刷新"""
        self._refresh_grid()
    
    def action_manage_agents(self):
        """打开智能体管理界面"""
        self.push_screen(AgentManagementScreen(self.store))
    
    def action_help(self):
        """显示帮助"""
        self.push_screen(HelpScreen())


class HelpScreen(ModalScreen):
    """帮助对话框"""
    
    BINDINGS = [
        ("escape", "close", "关闭"),
        ("q", "close", "关闭"),
    ]
    
    def compose(self) -> ComposeResult:
        with Grid(classes="dialog"):
            yield Static("⌨️  键盘快捷键", classes="dialog-title")
            help_text = """
主界面:
  ↑/↓     选择员工
  Enter   打开聊天
  m       管理智能体
  r       刷新列表
  q       退出程序
  ?       显示帮助

聊天界面:
  Tab     切换焦点
  Enter   发送消息
  ESC     返回主界面
  Ctrl+C  退出程序

命令行:
  mushtech_studio config      配置界面
  mushtech_studio reset       重置配置
            """
            yield Static(help_text.strip(), classes="help-text")
            with Horizontal(classes="dialog-buttons"):
                yield Button("关闭", id="close", classes="dialog-btn")
    
    def on_button_pressed(self, event: Button.Pressed):
        self.action_close()
    
    def action_close(self):
        self.app.pop_screen()


def main():
    """入口函数"""
    app = MushTechStudioApp()
    app.run()


if __name__ == "__main__":
    main()
