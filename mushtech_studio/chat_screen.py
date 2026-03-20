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
from textual import events
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
        ("f5", "sync_now", "立即同步"),
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
        self._connected_shown = False  # 标记是否已显示过连接成功消息
        self._thinking_timer = None  # 思考状态定时器
        self._streaming_widget: Optional[Static] = None  # 流式输出占位 widget
        
        # 定期同步机制（解决多客户端消息不同步问题）
        self._sync_timer: Optional[asyncio.Task] = None  # 同步定时器
        self._sync_interval = 10  # 同步间隔（秒）
        self._last_sync_count = 0  # 上次同步时的消息数量
        self._is_user_active = False  # 用户是否正在活跃操作（避免同步干扰）
        self._pending_sync = False  # 是否有待执行的同步
        self._activity_timer: Optional[asyncio.Task] = None  # 活跃状态定时器
        self._last_sync_time: Optional[datetime] = None  # 上次同步时间
    
    def compose(self):
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
                " [Tab]切换 [Enter]发送 [ESC]返回 [F5]同步 [Ctrl+C]退出",
                classes="footer-bar"
            )
    
    def on_mount(self):
        """初始化"""
        
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
        """从 OpenClaw 同步历史消息到本地（初始同步）
        
        只读 OpenClaw，将历史记录覆盖写入本地文件。
        """
        sync_success = False
        try:
            count = self.msg_manager.sync_from_openclaw(self.emp_id)
            self._last_sync_count = count
            self._last_sync_time = datetime.now()
            if count > 0:
                logger.info(f"[ChatScreen:{self.emp_id}] Initial sync: {count} messages from OpenClaw")

            sync_success = True
        except Exception as e:
            logger.error(f"[ChatScreen:{self.emp_id}] Failed to sync from OpenClaw: {e}")
        
        # 设置焦点到输入框并注册回调
        try:
            self.query_one("#message-input", Input).focus()
        except Exception:
            pass
        
        self.msg_manager.register_message_callback(self.emp_id, self._on_message_received)
        
        self._start_sync_timer()
        
        if not sync_success:
            self._update_status_text(f"🦞 [{self.employee.id}] {self.employee.name} - {self.employee.role} [⚠ 历史同步失败，将定期重试]")
    
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
        
        # 多订阅者模式下，不需要调用原始回调
        # 每个对话框只接收自己的消息（由 MessageManager 路由）
    
    def _clear_thinking_state(self):
        """清除思考状态（防止卡死）"""
        self.is_thinking = False
    
    def on_unmount(self):
        """卸载时注销回调并清理资源"""
        self.msg_manager.unregister_message_callback(self.emp_id)
        self._stop_sync_timer()
        if self._activity_timer is not None:
            self._activity_timer.cancel()
            self._activity_timer = None
        self.is_thinking = False
        self._thinking_timer = None
    
    def watch_connection_status(self, status: str):
        """监听连接状态变化"""
        self._update_status_bar()
    
    def watch_messages(self, messages: List[Message]):
        """监听消息变化，自动刷新显示"""
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
        except Exception:
            pass
    
    def _remove_thinking_indicator(self):
        """移除思考中指示器"""
        try:
            container = self.query_one("#messages-container", ScrollableContainer)
            for child in list(container.children):
                if hasattr(child, 'is_thinking_indicator'):
                    child.remove()
                    break
        except Exception:
            pass
    
    def _update_status_bar(self):
        """更新状态栏"""
        try:
            status = self.msg_manager.get_status(self.emp_id)
            
            # 构建状态文本
            base_text = f"🦞 [{self.employee.id}] {self.employee.name} - {self.employee.role}"
            
            # 添加上次同步时间
            sync_info = ""
            if self._last_sync_time:
                seconds_ago = int((datetime.now() - self._last_sync_time).total_seconds())
                if seconds_ago < 60:
                    sync_info = f" 同步:{seconds_ago}s前"
                else:
                    minutes_ago = seconds_ago // 60
                    sync_info = f" 同步:{minutes_ago}m前"
            
            if self.is_thinking:
                status_text = f"{base_text} [🤔 思考中...]{sync_info}"
            elif status == "connected" or self.msg_manager.is_connected(self.emp_id):
                status_text = f"{base_text} [✓ 已连接]{sync_info}"
            elif status == "connecting":
                status_text = f"{base_text} [连接中...]{sync_info}"
            else:
                status_text = f"{base_text} [✗ 未连接]{sync_info}"
            
            self._update_status_text(status_text)
        except Exception:
            pass
    
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
            

        except Exception:
            pass
    
    def on_input_submitted(self, event: Input.Submitted):
        """输入框提交"""
        if event.input.id == "message-input":
            self._send_message()
    
    def action_sync_now(self):
        """立即同步消息（手动触发）"""
        logger.info(f"[ChatScreen:{self.emp_id}] Manual sync triggered")
        self.run_worker(self._do_periodic_sync())
    
    def on_button_pressed(self, event: Button.Pressed):
        """按钮点击"""
        btn_id = event.button.id
        if btn_id == "send-btn":
            self._send_message()
        elif btn_id == "clear-btn":
            self._clear_messages()
        elif btn_id == "back-btn":
            self.action_go_back()
    
    def _start_sync_timer(self):
        """启动定期同步定时器"""
        if self._sync_timer is not None:
            return
        
        async def sync_loop():
            while True:
                try:
                    await asyncio.sleep(self._sync_interval)
                    await self._do_periodic_sync()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"[ChatScreen:{self.emp_id}] Sync error: {e}")
        
        self._sync_timer = asyncio.create_task(sync_loop())
        logger.debug(f"[ChatScreen:{self.emp_id}] Started sync timer ({self._sync_interval}s)")
    
    def _stop_sync_timer(self):
        """停止定期同步定时器"""
        if self._sync_timer is not None:
            self._sync_timer.cancel()
            self._sync_timer = None
            logger.debug(f"[ChatScreen:{self.emp_id}] Stopped sync timer")
    
    def _mark_user_active(self):
        """标记用户活跃状态，暂停自动同步避免干扰"""
        self._is_user_active = True
        
        # 取消之前的定时器
        if self._activity_timer is not None:
            self._activity_timer.cancel()
        
        # 3秒后恢复同步
        async def reset():
            await asyncio.sleep(3)
            self._is_user_active = False
            # 如果有待执行的同步，立即执行
            if self._pending_sync:
                self.run_worker(self._do_periodic_sync())
        
        self._activity_timer = asyncio.create_task(reset())
    
    async def _do_periodic_sync(self):
        """执行定期同步
        
        从 OpenClaw 同步新消息，解决多客户端消息不同步问题。
        智能合并：保留本地 WebSocket 已接收的消息，添加 OpenClaw 中新增的消息。
        """
        # 如果用户正在活跃操作或正在流式接收，推迟同步
        if self._is_user_active or self._streaming_widget is not None:
            self._pending_sync = True
            logger.debug(f"[ChatScreen:{self.emp_id}] Sync deferred (user active or streaming)")
            return
        
        try:
            # 获取当前本地消息数量
            local_count = len(self.messages)
            
            # 从 OpenClaw 同步（智能合并模式）
            new_count = self.msg_manager.sync_from_openclaw_incremental(self.emp_id)
            
            if new_count > 0:
                logger.info(f"[ChatScreen:{self.emp_id}] Periodic sync: {new_count} new messages from OpenClaw")
                # 更新消息列表
                self.messages = self.msg_manager.get_messages(self.emp_id)
                self._deduplicate_connect_messages()
                self._refresh_messages()
                # 显示同步提示
                self._show_sync_notification(new_count)
            
            self._last_sync_count = local_count + new_count
            self._last_sync_time = datetime.now()
            self._pending_sync = False
            
        except Exception as e:
            logger.error(f"[ChatScreen:{self.emp_id}] Periodic sync failed: {e}")
    
    def _show_sync_notification(self, count: int):
        """显示同步通知"""
        try:
            # 临时显示同步提示
            base_text = f"🦞 [{self.employee.id}] {self.employee.name} - {self.employee.role}"
            self._update_status_text(f"{base_text} [↻ 同步了 {count} 条新消息]")
            # 3秒后恢复
            self.app.set_timer(3, lambda: self._update_status_bar())
        except Exception:
            pass
    
    def _update_status_text(self, text: str):
        """更新状态栏文本"""
        try:
            status_widget = self.query_one("#chat-status", Static)
            status_widget.update(text)
        except Exception:
            pass
    
    def _on_activity(self):
        """记录用户活动，暂停同步"""
        self._mark_user_active()
    
    def _send_message(self):
        """发送消息 - 立即显示在对话框中"""
        input_widget = self.query_one("#message-input", Input)
        content = input_widget.value.strip()
        if not content:
            return
        
        # 标记用户活跃（防止同步干扰）
        self._mark_user_active()
        
        # 清空输入框
        input_widget.value = ""
        
        # 立即添加用户消息到本地并刷新UI
        self.msg_manager._add_user_message(self.emp_id, content)
        self.messages = self.msg_manager.get_messages(self.emp_id)
        self._deduplicate_connect_messages()
        self._refresh_messages()
        
        self.run_worker(self._do_send_background(content))
    
    async def _do_send_background(self, content: str):
        """后台发送消息 - 只处理响应（用户消息已经显示）"""
        self.is_thinking = True
        
        try:
            response = await self.msg_manager.send_message(self.emp_id, content)
        except Exception:
            pass
            # 添加错误提示并清除思考状态
            self.is_thinking = False
            self.msg_manager._add_system_message(self.emp_id, f"发送失败: {str(e)[:50]}")
            self.messages = self.msg_manager.get_messages(self.emp_id)
            self._refresh_messages()
    
    def _clear_messages(self):
        """清空消息"""
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
        self.app.pop_screen()
    
    def action_quit(self):
        """退出应用"""
        self.app.exit()
    
    def action_next_focus(self):
        """下一个焦点"""
        self.screen.focus_next()
    
    def action_prev_focus(self):
        """上一个焦点"""
        self.screen.focus_previous()
    
    def on_key(self, event: events.Key) -> None:
        """处理按键事件 - 标记用户活跃"""
        if event.key != "f5":
            self._mark_user_active()
