#!/usr/bin/env python3
"""
消息管理器 - 混合存储方案

存储策略：
- 本地存储: data/messages_<emp_id>.jsonl (每个 agent 独立文件)
- OpenClaw: 只读，进入对话框时同步历史到本地

同步机制：
- 进入对话框时: 从 OpenClaw session 读取 -> 覆盖写入本地
- 运行时: 新消息追加到本地文件
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime

from .models import Employee, EmployeeStore
from .client import MushTechClient, MushTechConfig
from .config_manager import get_config_manager
from .logger import logger


@dataclass
class Message:
    """单条消息"""
    sender: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_read: bool = False
    
    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp,
            "is_read": self.is_read
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            sender=data.get("sender", "unknown"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            is_read=data.get("is_read", False)
        )
    
    @classmethod
    def from_openclaw(cls, role: str, content: str, timestamp: int | str) -> "Message":
        """从 OpenClaw 消息格式创建"""
        if isinstance(timestamp, int):
            ts = datetime.fromtimestamp(timestamp / 1000).isoformat()
        else:
            ts = timestamp
        
        # 转换 role
        if role == "user":
            sender = "user"
        elif role == "assistant":
            sender = "assistant"
        elif role == "toolResult":
            sender = "tool"
        else:
            sender = role
        
        return cls(sender=sender, content=content, timestamp=ts, is_read=True)


@dataclass
class Conversation:
    """与单个员工的对话"""
    employee_id: str
    messages: List[Message] = field(default_factory=list)
    unread_count: int = 0
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_message(self, sender: str, content: str, is_read: bool = False) -> Message:
        """添加消息（运行时追加）"""
        msg = Message(sender=sender, content=content, timestamp=datetime.now().isoformat(), is_read=is_read)
        self.messages.append(msg)
        self.last_active = msg.timestamp
        if not is_read:
            self.unread_count += 1
        return msg
    
    def mark_as_read(self):
        """标记所有消息为已读"""
        for msg in self.messages:
            msg.is_read = True
        self.unread_count = 0
    
    def replace_messages(self, messages: List[Message]):
        """替换所有消息（用于同步时覆盖）"""
        self.messages = messages
        if messages:
            self.last_active = messages[-1].timestamp
        # 重新计算未读计数
        self.unread_count = sum(1 for m in messages if not m.is_read)


class OpenClawSessionReader:
    """读取 OpenClaw 的 session 文件（只读）"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.sessions_dir = Path.home() / ".openclaw" / "agents" / agent_id / "sessions"
        self.sessions_file = self.sessions_dir / "sessions.json"
    
    def get_session_file(self, session_key: str = "main") -> Optional[Path]:
        """从 sessions.json 获取 sessionFile（优先），回退到 sessionId 推导的 jsonl 文件。"""
        if not self.sessions_file.exists():
            return None

        try:
            data = json.loads(self.sessions_file.read_text(encoding='utf-8'))
            full_key = f"agent:{self.agent_id}:{session_key}"
            session_meta = data.get(full_key, {}) if isinstance(data, dict) else {}

            session_file = str(session_meta.get("sessionFile") or "").strip()
            if session_file:
                path = Path(session_file).expanduser()
                if path.exists():
                    return path

            session_id = str(session_meta.get("sessionId") or "").strip()
            if session_id:
                fallback = self.sessions_dir / f"{session_id}.jsonl"
                if fallback.exists():
                    return fallback
        except Exception as e:
            logger.error(f"Failed to resolve session file for {self.agent_id}: {e}")

        return None
    
    def read_messages(self, session_key: str = "main", limit: int = 200) -> List[Message]:
        """从 OpenClaw 读取消息历史（只读，不修改）"""
        session_file = self.get_session_file(session_key)
        if not session_file:
            return []
        
        messages = []
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event = json.loads(line)
                        if event.get("type") != "message":
                            continue
                        
                        msg_data = event.get("message", {})
                        role = msg_data.get("role", "unknown")
                        timestamp = event.get("timestamp", datetime.now().isoformat())
                        
                        # 提取内容
                        content_parts = msg_data.get("content", [])
                        content_text = self._extract_content(content_parts)
                        
                        if content_text:
                            msg = Message.from_openclaw(role, content_text, timestamp)
                            messages.append(msg)
                            
                    except (json.JSONDecodeError, Exception):
                        continue
            
            # 限制数量，保留最新的
            if len(messages) > limit:
                messages = messages[-limit:]
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to read session file: {e}")
            return []
    
    def _extract_content(self, content_parts: list) -> str:
        """从 OpenClaw content 提取文本"""
        texts = []
        for part in content_parts:
            if not isinstance(part, dict):
                continue
            
            part_type = part.get("type", "")
            
            if part_type == "text":
                text = part.get("text", "")
                if text:
                    texts.append(text)
            elif part_type == "thinking":
                thinking = part.get("thinking", "")
                if thinking:
                    texts.append(f"💭 {thinking}")
            elif part_type == "toolCall":
                tool_name = part.get("name", "unknown")
                texts.append(f"🔧 [使用工具: {tool_name}]")
            elif part_type == "toolResult":
                texts.append("[工具执行结果]")
        
        return "\n".join(texts)


class MessageManager:
    """消息管理器 - 本地存储 + OpenClaw 同步"""
    
    _instance: Optional["MessageManager"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, store: Optional[EmployeeStore] = None):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        self.store = store or EmployeeStore()
        
        # 从 config_manager 创建 WebSocket 配置
        studio_config = get_config_manager().get_config()
        self.config = MushTechConfig(
            base_url=studio_config.gateway_url,
            token=studio_config.gateway_token,
            timeout=120
        )
        
        # 对话存储
        self.conversations: Dict[str, Conversation] = {}
        
        # WebSocket 客户端
        self.clients: Dict[str, MushTechClient] = {}
        
        # 连接状态
        self.connection_status: Dict[str, str] = {}
        
        # UI 回调 - 支持多订阅者（解决"串台"问题）
        self._message_callbacks: Dict[str, Callable[[str, str, str], None]] = {}
        self.on_unread_changed: Optional[Callable[[str, int], None]] = None
        self.on_status_changed: Optional[Callable[[str, str], None]] = None
        # 保留向后兼容
        self.on_message_received: Optional[Callable[[str, str, str], None]] = None
        
        # 本地存储目录
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # 加载本地历史（不自动同步 OpenClaw，延迟到进入对话框时）
        self._load_all_local_messages()
        
        logger.info("MessageManager initialized")
    
    def _get_local_file(self, emp_id: str) -> Path:
        """获取指定员工的本地消息文件路径（按 agentname 命名，回退 emp_id）。"""
        emp = self.store.employees.get(emp_id)
        filename_key = emp.agent_id if emp and getattr(emp, "agent_id", "") else emp_id
        return self.data_dir / f"messages_{filename_key}.jsonl"
    
    def _load_local_messages(self, emp_id: str) -> List[Message]:
        """从本地文件加载指定员工的消息"""
        msg_file = self._get_local_file(emp_id)
        if not msg_file.exists():
            return []
        
        messages = []
        try:
            with open(msg_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if isinstance(data, dict) and data.get("__transport__"):
                            continue
                        messages.append(Message.from_dict(data))
                    except (json.JSONDecodeError, Exception):
                        continue
            return messages
        except Exception as e:
            logger.error(f"Failed to load local messages for {emp_id}: {e}")
            return []
    
    def _load_all_local_messages(self):
        """加载所有员工的本地消息"""
        for emp_id in self.store.employees.keys():
            messages = self._load_local_messages(emp_id)
            conv = Conversation(employee_id=emp_id)
            conv.messages = messages
            if messages:
                conv.last_active = messages[-1].timestamp
            self.conversations[emp_id] = conv
            logger.debug(f"Loaded {len(messages)} local messages for {emp_id}")
    
    def _save_message_local(self, emp_id: str, msg: Message):
        """追加单条消息到本地文件"""
        try:
            msg_file = self._get_local_file(emp_id)
            with open(msg_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(msg.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to save message locally: {e}")
    
    def _save_all_messages_local(self, emp_id: str, messages: List[Message]):
        """覆盖保存所有消息到本地文件（用于同步时覆盖）"""
        try:
            msg_file = self._get_local_file(emp_id)
            with open(msg_file, 'w', encoding='utf-8') as f:
                for msg in messages:
                    f.write(json.dumps(msg.to_dict(), ensure_ascii=False) + '\n')
            logger.info(f"Saved {len(messages)} messages to local file for {emp_id}")
        except Exception as e:
            logger.error(f"Failed to save messages locally: {e}")
    
    def _save_messages(self, emp_id: str):
        """保存指定员工的所有消息（用于清空消息等操作）"""
        conv = self.conversations.get(emp_id)
        if conv:
            self._save_all_messages_local(emp_id, conv.messages)
    
    def sync_from_openclaw(self, emp_id: str) -> int:
        """从 OpenClaw 同步历史消息到本地（覆盖本地）
        
        在首次进入对话框时调用，从 OpenClaw session 读取完整历史并覆盖本地。
        
        Returns:
            同步的消息数量
        """
        emp = self.store.employees.get(emp_id)
        if not emp or not emp.agent_id:
            return 0
        
        try:
            logger.info(f"Syncing messages from OpenClaw for {emp_id}...")
            
            # 从 OpenClaw 读取（只读）
            reader = OpenClawSessionReader(emp.agent_id)
            openclaw_messages = reader.read_messages(session_key="main", limit=200)
            
            if not openclaw_messages:
                logger.info(f"No messages found in OpenClaw for {emp_id}")
                return 0
            
            # 获取本地消息数量用于对比
            conv = self.get_conversation(emp_id)
            old_count = len(conv.messages)
            
            # 合并策略：保留本地未读状态，但内容以 OpenClaw 为准
            # 创建 timestamp -> is_read 的映射
            local_read_status = {m.timestamp: m.is_read for m in conv.messages}
            
            # 应用未读状态到 OpenClaw 消息
            for msg in openclaw_messages:
                if msg.timestamp in local_read_status:
                    msg.is_read = local_read_status[msg.timestamp]
            
            # 覆盖本地消息
            conv.replace_messages(openclaw_messages)
            
            # 覆盖写入本地文件
            self._save_all_messages_local(emp_id, openclaw_messages)
            
            new_count = len(openclaw_messages)
            logger.info(f"Synced {new_count} messages from OpenClaw for {emp_id} (local had {old_count})")
            
            return new_count
            
        except Exception as e:
            logger.error(f"Failed to sync from OpenClaw for {emp_id}: {e}")
            return 0
    
    def sync_from_openclaw_incremental(self, emp_id: str) -> int:
        """从 OpenClaw 增量同步新消息（智能合并）
        
        在对话框保持打开期间定期调用，只同步 OpenClaw 中有但本地没有的消息。
        保留本地通过 WebSocket 接收的消息，避免重复。
        
        Returns:
            新增的消息数量
        """
        emp = self.store.employees.get(emp_id)
        if not emp or not emp.agent_id:
            logger.debug(f"Incremental sync skipped for {emp_id}: no agent_id")
            return 0
        
        try:
            logger.debug(f"Starting incremental sync for {emp_id} (agent: {emp.agent_id})")
            
            # 从 OpenClaw 读取
            reader = OpenClawSessionReader(emp.agent_id)
            openclaw_messages = reader.read_messages(session_key="main", limit=200)
            
            if not openclaw_messages:
                logger.debug(f"Incremental sync for {emp_id}: OpenClaw has no messages")
                return 0
            
            conv = self.get_conversation(emp_id)
            local_count_before = len(conv.messages)
            
            logger.debug(f"Incremental sync for {emp_id}: OpenClaw has {len(openclaw_messages)}, local has {local_count_before}")
            
            # 创建本地消息的唯一标识集合（使用 content 前80字符的哈希）
            # 不使用 timestamp 因为 WebSocket 和 OpenClaw 的时间戳格式可能不同
            local_content_hashes = set()
            for m in conv.messages:
                # 标准化内容：去除首尾空格，取前80字符
                normalized = m.content.strip()[:80]
                content_hash = hash(f"{m.sender}:{normalized}")
                local_content_hashes.add(content_hash)
            
            # 找出 OpenClaw 中有但本地没有的消息
            new_messages = []
            for msg in openclaw_messages:
                normalized = msg.content.strip()[:80]
                content_hash = hash(f"{msg.sender}:{normalized}")
                if content_hash not in local_content_hashes:
                    new_messages.append(msg)
                    local_content_hashes.add(content_hash)  # 避免重复添加
            
            if not new_messages:
                logger.debug(f"Incremental sync for {emp_id}: no new messages to add")
                return 0
            
            logger.info(f"Incremental sync for {emp_id}: found {len(new_messages)} new messages to add")
            
            # 合并：保留本地消息，追加新消息
            # 按时间戳排序
            all_messages = conv.messages + new_messages
            all_messages.sort(key=lambda m: m.timestamp)
            
            # 限制数量（保留最新的200条）
            if len(all_messages) > 200:
                all_messages = all_messages[-200:]
            
            # 更新内存
            conv.replace_messages(all_messages)
            
            # 增量追加到本地文件（而不是覆盖）
            for msg in new_messages:
                self._save_message_local(emp_id, msg)
            
            logger.info(f"Incremental sync for {emp_id}: {len(new_messages)} new messages added (OpenClaw: {len(openclaw_messages)}, local was: {local_count_before})")
            return len(new_messages)
            
        except Exception as e:
            logger.error(f"Failed to incrementally sync from OpenClaw for {emp_id}: {e}")
            import traceback
            logger.debug(f"Incremental sync error traceback: {traceback.format_exc()}")
            return 0
    
    def get_conversation(self, emp_id: str) -> Conversation:
        """获取或创建对话"""
        if emp_id not in self.conversations:
            self.conversations[emp_id] = Conversation(employee_id=emp_id)
        return self.conversations[emp_id]
    
    def get_messages(self, emp_id: str) -> List[Message]:
        """获取员工的消息列表"""
        conv = self.get_conversation(emp_id)
        return conv.messages.copy()
    
    def get_unread_count(self, emp_id: str) -> int:
        """获取员工的未读消息数"""
        conv = self.conversations.get(emp_id)
        return conv.unread_count if conv else 0
    
    def get_total_unread(self) -> int:
        """获取总未读消息数"""
        return sum(conv.unread_count for conv in self.conversations.values())
    
    def mark_as_read(self, emp_id: str):
        """标记员工消息为已读"""
        conv = self.conversations.get(emp_id)
        if conv:
            old_count = conv.unread_count
            conv.mark_as_read()
            
            # 更新本地文件（覆盖，保持内容但标记已读）
            self._save_all_messages_local(emp_id, conv.messages)
            
            if old_count > 0 and self.on_unread_changed:
                try:
                    self.on_unread_changed(emp_id, 0)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
            logger.info(f"Marked messages as read for {emp_id}")
    
    async def connect_employee(self, emp_id: str) -> bool:
        """连接指定员工"""
        emp = self.store.employees.get(emp_id)
        if not emp:
            logger.error(f"Employee not found: {emp_id}")
            return False
        
        if emp_id in self.clients and self.clients[emp_id].is_connected:
            logger.debug(f"{emp_id} already connected")
            return True
        
        client = MushTechClient(
            employee=emp,
            config=self.config,
            on_message=lambda sender, content: self._handle_message(emp_id, sender, content),
            on_status_change=lambda status: self._handle_status_change(emp_id, status),
            on_transport=lambda direction, payload: self._handle_transport(emp_id, direction, payload),
        )
        
        self.clients[emp_id] = client
        
        try:
            success = await client.connect()
            if success:
                self.connection_status[emp_id] = "connected"
                logger.info(f"Connected to {emp_id}")
                return True
            else:
                self.connection_status[emp_id] = "failed"
                return False
        except Exception as e:
            logger.error(f"Failed to connect {emp_id}: {e}")
            self.connection_status[emp_id] = "error"
            return False
    
    async def connect_all(self):
        """连接所有启用的员工"""
        logger.info("Connecting all employees...")
        tasks = []
        for emp in self.store.employees.values():
            if emp.enabled:
                tasks.append(self.connect_employee(emp.id))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def disconnect_employee(self, emp_id: str):
        """断开指定员工"""
        client = self.clients.get(emp_id)
        if client:
            await client.close()
            del self.clients[emp_id]
            self.connection_status[emp_id] = "disconnected"
            logger.info(f"Disconnected from {emp_id}")
    
    async def disconnect_all(self):
        """断开所有员工"""
        logger.info("Disconnecting all employees...")
        for emp_id in list(self.clients.keys()):
            await self.disconnect_employee(emp_id)
    
    async def send_message(self, emp_id: str, content: str) -> Optional[str]:
        """发送消息给指定员工"""
        client = self.clients.get(emp_id)
        if not client or not client.is_connected:
            logger.error(f"Cannot send to {emp_id}: not connected")
            return None
        
        try:
            response = await client.send_message(content)
            return response
        except Exception as e:
            logger.error(f"Failed to send message to {emp_id}: {e}")
            return None
    
    def register_message_callback(self, emp_id: str, callback: Callable[[str, str, str], None]):
        """注册指定员工的消息回调（解决多对话框"串台"问题）"""
        self._message_callbacks[emp_id] = callback
        logger.debug(f"Registered message callback for {emp_id}")
    
    def unregister_message_callback(self, emp_id: str):
        """注销指定员工的消息回调"""
        if emp_id in self._message_callbacks:
            del self._message_callbacks[emp_id]
            logger.debug(f"Unregistered message callback for {emp_id}")
    
    def _handle_message(self, emp_id: str, sender: str, content: str):
        """处理收到的消息（WebSocket 回调）"""
        logger.info(f"Message from {emp_id}/{sender}: {content[:50]}...")
        
        # 先处理流式/思考状态通知（不保存到消息历史）
        if sender in ("__thinking__", "__stream__"):
            # 优先使用多订阅者回调（精确路由）
            callback = self._message_callbacks.get(emp_id)
            if callback:
                try:
                    callback(emp_id, sender, content)
                except Exception as e:
                    logger.error(f"Error in callback for {emp_id}: {e}")
            # 向后兼容
            elif self.on_message_received:
                try:
                    self.on_message_received(emp_id, sender, content)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
            return
        
        # 添加到对话
        conv = self.get_conversation(emp_id)
        is_read = sender == "system"
        msg = conv.add_message(sender, content, is_read)
        
        # 追加到本地文件
        self._save_message_local(emp_id, msg)
        
        # 通知 UI - 优先使用多订阅者回调（精确路由到对应对话框）
        callback = self._message_callbacks.get(emp_id)
        if callback:
            try:
                callback(emp_id, sender, content)
            except Exception as e:
                logger.error(f"Error in callback for {emp_id}: {e}")
        # 向后兼容
        elif self.on_message_received:
            try:
                self.on_message_received(emp_id, sender, content)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
        
        if self.on_unread_changed and not is_read:
            try:
                self.on_unread_changed(emp_id, conv.unread_count)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def _handle_status_change(self, emp_id: str, status: str):
        """处理连接状态变化"""
        logger.debug(f"Status change for {emp_id}: {status}")
        self.connection_status[emp_id] = status
        
        if self.on_status_changed:
            try:
                self.on_status_changed(emp_id, status)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    # 需要过滤的传输层心跳事件类型
    _TRANSPORT_NOISE_EVENTS = {"tick", "health"}

    def _handle_transport(self, emp_id: str, direction: str, payload: str):
        """记录 WS 收发信息到本地 messages 文件（仅落盘，不进入对话框）。
        
        自动过滤：
        - 心跳事件（tick、health）
        - 流式消息增量（chat 事件 state=delta）
        只保留完整消息（chat 事件 state=final）。
        """
        # 过滤心跳事件和流式增量：检查 payload 是否包含事件类型
        try:
            payload_data = json.loads(payload)
            event_type = payload_data.get("event") or payload_data.get("type")
            
            # 过滤心跳事件
            if event_type in self._TRANSPORT_NOISE_EVENTS:
                return
            
            # 过滤流式消息增量（只保留 final 状态的 chat 事件）
            if event_type == "chat":
                event_payload = payload_data.get("payload", {})
                state = event_payload.get("state") if isinstance(event_payload, dict) else None
                if state and state != "final":
                    return  # 跳过 delta 和 thinking 状态，只保留 final
        except (json.JSONDecodeError, Exception):
            pass  # 解析失败继续记录
        
        direction_label = "WS→" if direction == "send" else "WS←"
        record = {
            "__transport__": True,
            "direction": direction,
            "label": direction_label,
            "payload": payload[:2000],
            "timestamp": datetime.now().isoformat(),
        }
        try:
            msg_file = self._get_local_file(emp_id)
            with open(msg_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to save transport record: {e}")
    
    def _add_user_message(self, emp_id: str, content: str):
        """添加用户发送的消息（供UI调用）"""
        conv = self.get_conversation(emp_id)
        msg = conv.add_message("user", content, is_read=True)
        self._save_message_local(emp_id, msg)
    
    def _add_system_message(self, emp_id: str, content: str):
        """添加系统消息（供UI调用）"""
        conv = self.get_conversation(emp_id)
        msg = conv.add_message("system", content, is_read=True)
        self._save_message_local(emp_id, msg)
    
    def is_connected(self, emp_id: str) -> bool:
        """检查员工是否已连接"""
        client = self.clients.get(emp_id)
        return client.is_connected if client else False
    
    def get_status(self, emp_id: str) -> str:
        """获取员工连接状态"""
        return self.connection_status.get(emp_id, "disconnected")


# 全局消息管理器实例
_message_manager: Optional[MessageManager] = None


def get_message_manager(store: Optional[EmployeeStore] = None) -> MessageManager:
    """获取全局消息管理器实例"""
    global _message_manager
    if _message_manager is None:
        _message_manager = MessageManager(store)
    return _message_manager
