"""
聊天界面 - 与 OpenClaw 员工对话
使用 MessageManager 管理消息和连接
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from textual.screen import Screen
from textual.widgets import Static, Input, Button
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.reactive import reactive
from rich.text import Text
from rich.markdown import Markdown
from rich.console import Group

from .models import Employee
from .message_manager import MessageManager, Message
from .logger import logger


class ChatScreen(Screen):
    """聊天界面 - 纯键盘操作"""
    
    CSS = """
    .chat-container {
        width: 100%;
        height: 100%;
        background: black;
        color: green;
    }
    .chat-status-bar {
        height: 1;
        background: $surface-darken-1;
        color: green;
        padding: 0 1;
        content-align: center middle;
    }
    .chat-messages {
        width: 100%;
        height: 1fr;
        background: black;
        border: solid green;
        padding: 0 1;
    }
    .chat-input-area {
        height: 3;
        background: $surface-darken-1;
    }
    .chat-input {
        width: 1fr;
        background: black;
        color: green;
        border: solid green;
    }
    .chat-input:focus {
        background: green;
        color: black;
    }
    .chat-btn {
        width: 10;
        background: black;
        color: green;
        border: solid green;
    }
    .chat-btn:focus {
        background: green;
        color: black;
    }
    .message {
        padding: 0 1;
        margin: 1 0;
    }
    .message-user {
        color: cyan;
    }
    .message-agent {
        color: green;
    }
    .message-system {
        color: yellow;
        text-style: dim;
    }
    .footer-bar {
        height: 1;
        background: black;
        color: green;
    }
    """
    
    BINDINGS = [
        ("escape", "go_back", "返回"),
        ("ctrl+c", "quit", "退出"),
        ("tab", "next_focus", "下一个"),
        ("shift+tab", "prev_focus", "上一个"),
    ]
    
    # 使用 reactive 自动刷新消息列表
    messages: reactive[List[Message]] = reactive(list)
    connection_status: reactive[str] = reactive("disconnected")
    is_thinking: reactive[bool] = reactive(False)  # 思考状态
    
    def __init__(self, employee: Employee, msg_manager: MessageManager):
        super().__init__()
        self.employee = employee
        self.msg_manager = msg_manager
        self.emp_id = employee.id
        self._original_callback = None
        self._connected_shown = False  # 标记是否已显示过连接成功消息
        self._thinking_timer = None  # 思考状态定时器
        self._streaming_widget: Optional[Static] = None  # 流式输出占位 widget
        # logger.info(f"[ChatScreen:{self.emp_id}] Initialized")
    
    def compose(self):
        # logger.debug(f"[ChatScreen:{self.emp_id}] Composing UI")
        with Vertical(classes="chat-container"):
            # 状态栏（顶部）
            yield Static(
                f"🦞 [{self.employee.id}] {self.employee.name} - {self.employee.role} [连接中...]",
                id="chat-status",
                classes="chat-status-bar"
            )
            
            # 消息区域（中间）
            with ScrollableContainer(id="messages-container", classes="chat-messages"):
                pass
            
            # 输入区域（底部）
            with Horizontal(classes="chat-input-area"):
                yield Input(
                    placeholder="输入消息...",
                    id="message-input",
                    classes="chat-input"
                )
                yield Button("发送", id="send-btn", classes="chat-btn")
                yield Button("清屏", id="clear-btn", classes="chat-btn")
                yield Button("返回", id="back-btn", classes="chat-btn")
            
            # 底部提示栏
            yield Static(
                " [Tab] 切换焦点 | [Enter] 发送/点击 | [ESC] 返回 | [Ctrl+C] 退出",
                classes="footer-bar"
            )
    
    def on_mount(self):
        """初始化"""
        # logger.info(f"[ChatScreen:{self.emp_id}] Mounted")
        
        # 从 OpenClaw 同步历史消息到本地（覆盖本地）
        self._sync_history_from_openclaw()
        
        # 加载历史消息
        self.messages = self.msg_manager.get_messages(self.emp_id)
        
        # 过滤掉重复的"已连接"系统消息，只保留最新的连接状态
        self._deduplicate_connect_messages()
        
        self._refresh_messages()
        
        # 检查当前连接状态
        if self.msg_manager.is_connected(self.emp_id):
            self.connection_status = "connected"
            self._update_status_bar()
        else:
            # 确保已连接
            self.run_worker(self._ensure_connection())
    
    def _sync_history_from_openclaw(self):
        """从 OpenClaw 同步历史消息到本地
        
        只读 OpenClaw，将历史记录覆盖写入本地文件。
        """
        try:
            count = self.msg_manager.sync_from_openclaw(self.emp_id)
            if count > 0:
                logger.info(f"[ChatScreen:{self.emp_id}] Synced {count} messages from OpenClaw")
        except Exception as e:
            logger.error(f"[ChatScreen:{self.emp_id}] Failed to sync from OpenClaw: {e}")
        
        # 设置焦点到输入框
        self.query_one("#message-input", Input).focus()
        
        # 设置消息接收回调
        self._original_callback = self.msg_manager.on_message_received
        self.msg_manager.on_message_received = self._on_message_received
    
    def _deduplicate_connect_messages(self):
        """去重连接消息，只保留最新的连接状态"""
        # 过滤掉所有"已连接到"的系统消息
        filtered = []
        for msg in self.messages:
            if msg.sender == "system" and "已连接到" in msg.content:
                continue
            filtered.append(msg)
        self.messages = filtered
    
    async def _ensure_connection(self):
        """确保连接"""
        success = await self.msg_manager.connect_employee(self.emp_id)
        if success:
            self.connection_status = "connected"
            self._connected_shown = True
        else:
            self.connection_status = "disconnected"
        self._update_status_bar()
    
    def _on_message_received(self, emp_id: str, sender: str, content: str):
        """收到消息回调 - 此方法在 asyncio 事件循环中被调用"""
        if emp_id == self.emp_id:
            # logger.info(f"[ChatScreen:{self.emp_id}] Message received from {sender}: {content[:50]}...")
            
            # 处理特殊发送者 - 思考状态通知
            if sender == "__thinking__":
                # 使用 call_later 确保在主线程更新UI（asyncio 事件循环中安全调用）
                def set_thinking():
                    self.is_thinking = True
                self.app.call_later(set_thinking)
                return
            
            # 处理流式输出 - 直接在原有 widget 上更新，不做全量刷新
            if sender == "__stream__":
                def update_stream(text=content):
                    # 切换到流式状态，清除「思考中」提示
                    self.is_thinking = False
                    self._update_streaming_widget(text)
                self.app.call_later(update_stream)
                return
            
            # 使用 call_later 确保在主线程更新UI
            def update_ui():
                # 收到实际回复，清除思考状态和流式 widget
                if sender == self.employee.name or sender not in ["system", "user"]:
                    self.is_thinking = False
                    self._remove_streaming_widget()
                
                # 更新消息列表（这会触发 watch_messages 自动刷新）
                self.messages = self.msg_manager.get_messages(self.emp_id)
            
            # 在主线程执行UI更新
            self.app.call_later(update_ui)
        
        # 调用原始回调
        if self._original_callback:
            try:
                self._original_callback(emp_id, sender, content)
            except Exception as e:
                pass  # logger.debug(f"[ChatScreen:{self.emp_id}] Original callback error: {e}")
    
    def _clear_thinking_state(self):
        """清除思考状态（防止卡死）"""
        self.is_thinking = False
    
    def on_unmount(self):
        """卸载时恢复回调并清理资源"""
        # logger.info(f"[ChatScreen:{self.emp_id}] Unmounting")
        if self._original_callback:
            self.msg_manager.on_message_received = self._original_callback
        # 清除思考状态（不需要关闭定时器，它会自动超时）
        self.is_thinking = False
        self._thinking_timer = None
    
    def watch_connection_status(self, status: str):
        """监听连接状态变化"""
        self._update_status_bar()
    
    def watch_messages(self, messages: List[Message]):
        """监听消息变化，自动刷新显示"""
        # logger.debug(f"[ChatScreen:{self.emp_id}] Messages updated: {len(messages)} messages")
        self._deduplicate_connect_messages()
        self._refresh_messages()
    
    def watch_is_thinking(self, thinking: bool):
        """监听思考状态变化"""
        self._update_status_bar()
        if thinking:
            # 添加思考中提示消息
            self._add_thinking_indicator()
        else:
            # 移除思考中提示
            self._remove_thinking_indicator()
    
    def _update_streaming_widget(self, text: str):
        """创建或更新流式输出 widget（不做全量刷新，直接 update）"""
        try:
            container = self.query_one("#messages-container", ScrollableContainer)
            if self._streaming_widget is None:
                # 首次：创建流式 widget 并挂载到底部
                markdown_body = Markdown(text)
                renderable = Group(Text("[🤖]"), markdown_body)
                widget = Static(renderable, classes="message message-agent")
                widget.is_streaming_widget = True  # type: ignore
                container.mount(widget)
                self._streaming_widget = widget
            else:
                # 后续 token：直接更新现有 widget 内容
                markdown_body = Markdown(text)
                renderable = Group(Text("[🤖]"), markdown_body)
                self._streaming_widget.update(renderable)
            container.scroll_end()
        except Exception as e:
            logger.debug(f"[ChatScreen:{self.emp_id}] Failed to update streaming widget: {e}")
    
    def _remove_streaming_widget(self):
        """移除流式 widget（收到 final 消息后调用）"""
        if self._streaming_widget is not None:
            try:
                self._streaming_widget.remove()
            except Exception:
                pass
            self._streaming_widget = None
    
    def _add_thinking_indicator(self):
        """添加思考中指示器"""
        try:
            container = self.query_one("#messages-container", ScrollableContainer)
            # 检查是否已存在思考指示器
            for child in list(container.children):
                if hasattr(child, 'is_thinking_indicator'):
                    return
            
            # 创建思考指示器
            indicator = Static(Text("[🤔] 正在思考..."), classes="message message-system")
            indicator.is_thinking_indicator = True
            container.mount(indicator)
            container.scroll_end()
        except Exception as e:
            pass  # logger.debug(f"[ChatScreen:{self.emp_id}] Failed to add thinking indicator: {e}")
    
    def _remove_thinking_indicator(self):
        """移除思考中指示器"""
        try:
            container = self.query_one("#messages-container", ScrollableContainer)
            for child in list(container.children):
                if hasattr(child, 'is_thinking_indicator'):
                    child.remove()
                    break
        except Exception as e:
            pass  # logger.debug(f"[ChatScreen:{self.emp_id}] Failed to remove thinking indicator: {e}")
    
    def _update_status_bar(self):
        """更新状态栏"""
        try:
            status_widget = self.query_one("#chat-status", Static)
            status = self.msg_manager.get_status(self.emp_id)
            
            # 构建状态文本
            base_text = f"🦞 [{self.employee.id}] {self.employee.name} - {self.employee.role}"
            
            if self.is_thinking:
                status_text = f"{base_text} [🤔 思考中...]"
            elif status == "connected" or self.msg_manager.is_connected(self.emp_id):
                status_text = f"{base_text} [✓ 已连接]"
            elif status == "connecting":
                status_text = f"{base_text} [连接中...]"
            else:
                status_text = f"{base_text} [✗ 未连接]"
            
            status_widget.update(status_text)
        except Exception as e:
            pass  # logger.warning(f"[ChatScreen:{self.emp_id}] Failed to update status bar: {e}")
    
    def _format_time(self, timestamp: str) -> str:
        """格式化时间戳为 HH:MM"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime("%H:%M")
        except:
            return ""
    
    def _create_message_widget(self, msg: Message) -> Static:
        """创建消息组件 - 带头像、时间、边框，支持 Markdown"""
        from rich.panel import Panel
        
        time_str = self._format_time(msg.timestamp)
        
        if msg.sender == "user":
            emoji = "👤"
            name = "你"
            css_class = "message-user"
            color = "cyan"
            # 标题：emoji + 名字(彩色) + 时间(淡色)
            title = Text.from_markup(f"{emoji} [{color}]{name}[/{color}] [dim]{time_str}[/dim]")
        elif msg.sender == "system":
            # 系统消息：简单显示
            return Static(
                Text.from_markup(f"[dim yellow]* {msg.content}[/dim yellow]"),
                classes="message message-system"
            )
        else:
            # Agent消息
            emoji = self.employee.emoji
            name = self.employee.display_name or self.employee.name
            css_class = "message-agent"
            color = "green"
            # 标题：emoji + 名字(彩色) + 时间(淡色)
            title = Text.from_markup(f"{emoji} [{color}]{name}[/{color}] [dim]{time_str}[/dim]")
        
        # 使用 Panel 创建带边框的气泡效果，内部使用 Markdown
        content_md = Markdown(msg.content or "")
        
        # 创建 Panel，使用标题栏显示头像和时间
        panel = Panel(
            content_md,
            title=title,
            title_align="left",
            border_style=color,
            padding=(0, 1),
        )
        
        return Static(panel, classes=f"message {css_class}")
    
    def _refresh_messages(self):
        """刷新消息显示"""
        try:
            container = self.query_one("#messages-container", ScrollableContainer)
            
            # 全量刷新时清除 streaming widget 引用（widget 会随 children 一起被移除）
            self._streaming_widget = None
            
            # 移除所有子组件
            for widget in list(container.children):
                widget.remove()
            
            # 添加新的消息组件
            for msg in self.messages[-100:]:
                widget = self._create_message_widget(msg)
                container.mount(widget)
            
            # 如果正在思考，重新添加思考指示器
            if self.is_thinking:
                self._add_thinking_indicator()
            
            # 滚动到底部
            container.scroll_end()
            
            # logger.debug(f"[ChatScreen:{self.emp_id}] Refreshed {len(self.messages)} messages")
        except Exception as e:
            pass  # logger.error(f"[ChatScreen:{self.emp_id}] Failed to refresh messages: {e}")
    
    def on_input_submitted(self, event: Input.Submitted):
        """输入框提交"""
        # logger.debug(f"[ChatScreen:{self.emp_id}] Input submitted")
        if event.input.id == "message-input":
            self._send_message()
    
    def on_button_pressed(self, event: Button.Pressed):
        """按钮点击"""
        btn_id = event.button.id
        # logger.info(f"[ChatScreen:{self.emp_id}] Button pressed: {btn_id}")
        if btn_id == "send-btn":
            self._send_message()
        elif btn_id == "clear-btn":
            self._clear_messages()
        elif btn_id == "back-btn":
            self.action_go_back()
    
    def _send_message(self):
        """发送消息 - 立即显示在对话框中"""
        input_widget = self.query_one("#message-input", Input)
        content = input_widget.value.strip()
        if not content:
            return
        
        # logger.info(f"[ChatScreen:{self.emp_id}] Sending message: {content[:50]}...")
        
        # 清空输入框
        input_widget.value = ""
        
        # 立即添加用户消息到本地并刷新UI
        self.msg_manager._add_user_message(self.emp_id, content)
        self.messages = self.msg_manager.get_messages(self.emp_id)
        self._deduplicate_connect_messages()
        self._refresh_messages()
        
        # 后台发送（不阻塞UI）
        self.run_worker(self._do_send_background(content))
    
    async def _do_send_background(self, content: str):
        """后台发送消息 - 只处理响应（用户消息已经显示）"""
        # 立即显示思考状态
        self.is_thinking = True
        # logger.info(f"[ChatScreen:{self.emp_id}] Agent is thinking...")
        
        try:
            response = await self.msg_manager.send_message(self.emp_id, content)
            # 响应会通过 on_message 回调自动更新UI
            # logger.debug(f"[ChatScreen:{self.emp_id}] Message sent successfully")
        except Exception as e:
            pass  # logger.error(f"[ChatScreen:{self.emp_id}] Failed to send message: {e}")
            # 添加错误提示并清除思考状态
            self.is_thinking = False
            self.msg_manager._add_system_message(self.emp_id, f"发送失败: {str(e)[:50]}")
            self.messages = self.msg_manager.get_messages(self.emp_id)
            self._refresh_messages()
    
    def _clear_messages(self):
        """清空消息"""
        # logger.info(f"[ChatScreen:{self.emp_id}] Clearing messages")
        # 重新初始化空对话
        conv = self.msg_manager.get_conversation(self.emp_id)
        conv.messages.clear()
        conv.unread_count = 0
        self.msg_manager._save_messages(self.emp_id)
        
        self.messages = []
        self._connected_shown = False
        self._refresh_messages()
        
        # 添加系统消息
        self.msg_manager._add_system_message(self.emp_id, "消息已清空")
        self.messages = self.msg_manager.get_messages(self.emp_id)
        self._refresh_messages()
    
    def action_go_back(self):
        """返回主界面"""
        # logger.info(f"[ChatScreen:{self.emp_id}] Going back to main screen")
        self.app.pop_screen()
    
    def action_quit(self):
        """退出应用"""
        # logger.info(f"[ChatScreen:{self.emp_id}] Quitting app")
        self.app.exit()
    
    def action_next_focus(self):
        """下一个焦点"""
        # logger.debug(f"[ChatScreen:{self.emp_id}] Next focus")
        self.screen.focus_next()
    
    def action_prev_focus(self):
        """上一个焦点"""
        # logger.debug(f"[ChatScreen:{self.emp_id}] Previous focus")
        self.screen.focus_previous()
