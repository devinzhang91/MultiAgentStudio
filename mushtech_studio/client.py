"""
OpenClaw WebSocket 客户端
基于 openclaw_service.py 的通信协议
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional, Callable

import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .models import Employee
from .logger import logger


@dataclass
class MushTechConfig:
    """OpenClaw WebSocket 连接配置"""
    base_url: str = "http://127.0.0.1:18789"
    token: str = ""
    timeout: int = 120
    
    @property
    def ws_url(self) -> str:
        """将 http/https 转换为 ws/wss"""
        if self.base_url.startswith("https://"):
            return self.base_url.replace("https://", "wss://")
        elif self.base_url.startswith("http://"):
            return self.base_url.replace("http://", "ws://")
        return self.base_url
    
    @property
    def origin(self) -> str:
        """获取 Origin"""
        return self.base_url


def _now_ms() -> int:
    return int(time.time() * 1000)



def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


class MushTechClient:
    """OpenClaw WebSocket 客户端（支持多员工）"""

    def __init__(self, employee: Employee, config: "MushTechConfig", 
                 on_message: Optional[Callable[[str, str], None]] = None,
                 on_status_change: Optional[Callable[[str], None]] = None,
                 on_transport: Optional[Callable[[str, str], None]] = None):
        self.employee = employee
        self.config = config
        self.on_message = on_message
        self.on_status_change = on_status_change
        self.on_transport = on_transport
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._recv_task: Optional[asyncio.Task] = None
        self._conn_lock = asyncio.Lock()

        self._rpc_waiters: dict[str, asyncio.Future] = {}
        self._task_waiters: dict[str, asyncio.Future] = {}

        self._connect_nonce: str = ""
        self._hello_ok = asyncio.Event()

        self._connected = False
        self._connecting = False
        self._closed = False

        self._device_id = ""
        self._device_public_key_raw_b64url = ""
        self._device_private_key: Optional[Ed25519PrivateKey] = None
        
        logger.debug(f"[{employee.id}] Client initialized, ws_url={config.ws_url}")

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws and not self._ws.closed

    def _identity_path(self) -> Path:
        """设备身份文件路径"""
        data_dir = Path(__file__).parent.parent / "data" / "identities"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / f"{self.employee.id}.json"

    def _load_or_create_identity(self):
        """加载或创建设备身份"""
        path = self._identity_path()
        logger.debug(f"[{self.employee.id}] Loading identity from {path}")

        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                private_key_pem = str(payload.get("private_key_pem", "")).strip()
                if private_key_pem:
                    private_key = serialization.load_pem_private_key(
                        private_key_pem.encode("utf-8"),
                        password=None,
                    )
                    if isinstance(private_key, Ed25519PrivateKey):
                        public_key_raw = private_key.public_key().public_bytes(
                            encoding=serialization.Encoding.Raw,
                            format=serialization.PublicFormat.Raw,
                        )
                        self._device_private_key = private_key
                        self._device_id = hashlib.sha256(public_key_raw).hexdigest()
                        self._device_public_key_raw_b64url = _b64url(public_key_raw)
                        logger.info(f"[{self.employee.id}] Identity loaded, device_id={self._device_id[:16]}...")
                        return
            except Exception as exc:
                logger.warning(f"[{self.employee.id}] Failed to load identity, creating new: {exc}")

        # 创建新密钥对
        logger.info(f"[{self.employee.id}] Creating new Ed25519 identity...")
        private_key = Ed25519PrivateKey.generate()
        public_key_raw = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        device_id = hashlib.sha256(public_key_raw).hexdigest()

        public_key_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        data = {
            "version": 1,
            "device_id": device_id,
            "public_key_pem": public_key_pem,
            "private_key_pem": private_key_pem,
            "created_at_ms": _now_ms(),
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

        self._device_private_key = private_key
        self._device_id = device_id
        self._device_public_key_raw_b64url = _b64url(public_key_raw)
        logger.info(f"[{self.employee.id}] New identity created, device_id={device_id[:16]}...")

    def _build_device_signature_payload(
        self,
        *,
        device_id: str,
        client_id: str,
        client_mode: str,
        role: str,
        scopes: list[str],
        signed_at_ms: int,
        token: str,
        nonce: str,
    ) -> str:
        return "|".join(
            [
                "v2",
                device_id,
                client_id,
                client_mode,
                role,
                ",".join(scopes),
                str(signed_at_ms),
                token or "",
                nonce,
            ]
        )

    def _build_device_payload(
        self,
        *,
        client_id: str,
        client_mode: str,
        scopes: list[str],
        token: str,
        nonce: str,
    ) -> dict[str, Any]:
        if not self._device_private_key:
            raise RuntimeError("Device identity not loaded")

        signed_at_ms = _now_ms()
        payload = self._build_device_signature_payload(
            device_id=self._device_id,
            client_id=client_id,
            client_mode=client_mode,
            role="operator",
            scopes=scopes,
            signed_at_ms=signed_at_ms,
            token=token,
            nonce=nonce,
        )
        signature = self._device_private_key.sign(payload.encode("utf-8"))
        return {
            "id": self._device_id,
            "publicKey": self._device_public_key_raw_b64url,
            "signature": _b64url(signature),
            "signedAt": signed_at_ms,
            "nonce": nonce,
        }

    async def connect(self) -> bool:
        """建立 WebSocket 连接并完成握手"""
        if self._connected:
            logger.debug(f"[{self.employee.id}] Already connected")
            return True
        
        if self._connecting:
            logger.debug(f"[{self.employee.id}] Connection in progress, waiting...")
            for _ in range(50):
                if self._connected:
                    return True
                await asyncio.sleep(0.1)
            return False

        async with self._conn_lock:
            if self._connected:
                return True
            
            self._connecting = True
            try:
                await self._do_connect()
                return self._connected
            except asyncio.TimeoutError:
                logger.error(f"[{self.employee.id}] Connection timeout")
                await self._cleanup_before_reconnect()
                self._update_status("error")
                raise
            except Exception as exc:
                logger.error(f"[{self.employee.id}] Connection failed: {exc}")
                await self._cleanup_before_reconnect()
                self._update_status("error")
                raise
            finally:
                self._connecting = False

    async def _do_connect(self):
        """执行连接"""
        logger.info(f"[{self.employee.id}] Starting connection to {self.config.ws_url}")
        
        self._load_or_create_identity()
        await self._cleanup_before_reconnect()

        ws_url = self.config.ws_url
        headers = {"Origin": self.config.origin} if self.config.origin else None
        
        logger.debug(f"[{self.employee.id}] Creating WebSocket connection...")
        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(
            ws_url,
            headers=headers,
            heartbeat=30,
        )
        logger.debug(f"[{self.employee.id}] WebSocket connected, waiting for challenge...")

        self._connect_nonce = ""
        self._hello_ok.clear()
        self._recv_task = asyncio.create_task(self._recv_loop())

        await self._wait_for_challenge(timeout=10)
        logger.debug(f"[{self.employee.id}] Challenge received, nonce={self._connect_nonce[:16]}...")
        
        await self._connect_handshake(timeout=15)
        logger.debug(f"[{self.employee.id}] Handshake completed")

        self._connected = True
        self._update_status("idle")
        logger.info(f"[{self.employee.id}] Connected successfully")

    async def _cleanup_before_reconnect(self):
        """清理之前的连接"""
        logger.debug(f"[{self.employee.id}] Cleaning up before reconnect")
        
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except Exception:
                pass

        if self._ws and not self._ws.closed:
            await self._ws.close()

        if self._session and not self._session.closed:
            await self._session.close()

        self._ws = None
        self._session = None
        self._recv_task = None
        self._connected = False

        self._wake_all_waiters(RuntimeError("OpenClaw reconnecting"))

    async def _wait_for_challenge(self, timeout: float):
        """等待 challenge nonce"""
        deadline = time.monotonic() + timeout
        while not self._connect_nonce:
            if time.monotonic() > deadline:
                raise TimeoutError("OpenClaw connect.challenge timeout")
            await asyncio.sleep(0.05)

    async def _connect_handshake(self, timeout: float):
        """发送 connect RPC 完成握手"""
        scopes_env = os.getenv("OPENCLAW_GATEWAY_SCOPES", "operator.admin")
        scopes = [x.strip() for x in scopes_env.split(",") if x.strip()]

        client_id = os.getenv("OPENCLAW_GATEWAY_CLIENT_ID", "openclaw-control-ui")
        client_mode = os.getenv("OPENCLAW_GATEWAY_CLIENT_MODE", "ui")

        params: dict[str, Any] = {
            "minProtocol": 3,
            "maxProtocol": 3,
            "client": {
                "id": client_id,
                "version": "1.0.0",
                "platform": "openclaw-tui-studio",
                "mode": client_mode,
                "instanceId": f"tui-{self.employee.id}",
            },
            "role": "operator",
            "scopes": scopes,
            "caps": [],
            "locale": "zh-CN",
            "device": self._build_device_payload(
                client_id=client_id,
                client_mode=client_mode,
                scopes=scopes,
                token=self.config.token,
                nonce=self._connect_nonce,
            ),
        }

        if self.config.token:
            params["auth"] = {"token": self.config.token}

        logger.debug(f"[{self.employee.id}] Sending connect RPC...")
        res = await self._rpc("connect", params=params, timeout_s=timeout)
        logger.debug(f"[{self.employee.id}] Connect response: {res}")
        
        if isinstance(res, dict) and res.get("type") == "hello-ok":
            self._hello_ok.set()

        await asyncio.wait_for(self._hello_ok.wait(), timeout=timeout)

    async def send_message(self, content: str) -> str:
        """发送聊天消息，等待最终回复
        
        会话隔离：每个 agent_id 对应独立的 session_key
        格式: agent:<agentId>:<mainKey>
        """
        if not await self.connect():
            raise ConnectionError("未连接到 OpenClaw Gateway")

        self._update_status("working")
        task_id = str(uuid.uuid4())
        fut = asyncio.get_running_loop().create_future()
        self._task_waiters[task_id] = fut

        # 优先使用 employee 的 session_key（格式: agent:<agentId>:main）
        # 这确保了不同 agent_id 的会话完全隔离
        raw_session_key = self.employee.session_key or self.employee.config.get("session_key")
        if not raw_session_key and self.employee.agent_id:
            # 动态生成 session_key
            raw_session_key = f"agent:{self.employee.agent_id}:main"
        
        session_key = self._normalize_chat_session_key(raw_session_key or self.employee.name.lower())
        
        payload = {
            "sessionKey": session_key,
            "message": content,
            "deliver": False,
            "idempotencyKey": task_id,
        }

        logger.info(f"[{self.employee.id}] Sending message: {content[:50]}...")
        logger.debug(f"[{self.employee.id}] Payload: {payload}")

        try:
            await self._rpc("chat.send", params=payload, timeout_s=15)
            logger.debug(f"[{self.employee.id}] Waiting for response...")
            result = await asyncio.wait_for(fut, timeout=self.config.timeout)
            logger.info(f"[{self.employee.id}] Response received: {str(result)[:100]}...")
            self._update_status("idle")
            return str(result)
        except asyncio.TimeoutError:
            logger.error(f"[{self.employee.id}] Request timeout")
            self._update_status("error")
            raise TimeoutError(f"请求超时（>{self.config.timeout}s）")
        finally:
            self._task_waiters.pop(task_id, None)

    async def _rpc(self, method: str, params: Any, timeout_s: float) -> Any:
        """发送 RPC 请求"""
        if not self._ws or self._ws.closed:
            raise RuntimeError("WebSocket 未连接")

        req_id = str(uuid.uuid4())
        fut = asyncio.get_running_loop().create_future()
        self._rpc_waiters[req_id] = fut

        frame = {
            "type": "req",
            "id": req_id,
            "method": method,
            "params": params,
        }
        
        logger.debug(f"[{self.employee.id}] RPC -> {method} (id={req_id[:8]})")
        if self.on_transport:
            try:
                self.on_transport("send", json.dumps(frame, ensure_ascii=False))
            except Exception:
                pass
        await self._ws.send_str(json.dumps(frame, ensure_ascii=False))

        try:
            result = await asyncio.wait_for(fut, timeout=timeout_s)
            logger.debug(f"[{self.employee.id}] RPC <- {method} success")
            return result
        except asyncio.TimeoutError:
            logger.error(f"[{self.employee.id}] RPC timeout: {method}")
            raise
        finally:
            self._rpc_waiters.pop(req_id, None)

    async def _recv_loop(self):
        """接收消息循环"""
        logger.debug(f"[{self.employee.id}] Receive loop started")
        try:
            assert self._ws is not None
            async for msg in self._ws:
                if self._closed:
                    break
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                logger.debug(f"[{self.employee.id}] WS recv: {msg.data[:200]}...")
                if self.on_transport:
                    try:
                        self.on_transport("recv", str(msg.data))
                    except Exception:
                        pass
                await self._handle_frame(str(msg.data))
        except asyncio.CancelledError:
            logger.debug(f"[{self.employee.id}] Receive loop cancelled")
        except Exception as exc:
            if not self._closed:
                logger.error(f"[{self.employee.id}] Receive error: {exc}")
        finally:
            if not self._closed:
                self._connected = False
                self._update_status("offline")
                self._wake_all_waiters(RuntimeError("WebSocket 断开"))

    async def _handle_frame(self, raw: str):
        """处理接收到的消息帧"""
        try:
            frame = json.loads(raw)
        except Exception:
            logger.warning(f"[{self.employee.id}] Failed to parse frame: {raw[:100]}")
            return

        frame_type = frame.get("type")

        if frame_type == "res":
            req_id = str(frame.get("id", ""))
            fut = self._rpc_waiters.get(req_id)
            if fut and not fut.done():
                if frame.get("ok"):
                    fut.set_result(frame.get("payload"))
                    logger.debug(f"[{self.employee.id}] RPC response OK for {req_id[:8]}")
                else:
                    err = frame.get("error")
                    logger.error(f"[{self.employee.id}] RPC error: {err}")
                    fut.set_exception(RuntimeError(str(err) if err else "RPC 失败"))
            return

        if frame_type == "event":
            event = frame.get("event")
            payload = frame.get("payload")

            if event == "connect.challenge" and isinstance(payload, dict):
                self._connect_nonce = str(payload.get("nonce", "")).strip()
                logger.debug(f"[{self.employee.id}] Got challenge nonce")
                return

            if event == "chat" and isinstance(payload, dict):
                await self._handle_chat_event(payload)
                return

        if frame_type == "hello-ok":
            logger.debug(f"[{self.employee.id}] Got hello-ok")
            self._hello_ok.set()

    async def _handle_chat_event(self, payload: dict[str, Any]):
        """处理聊天事件"""
        state = payload.get("state")
        logger.debug(f"[{self.employee.id}] Chat event, state={state}")
        
        # 只处理 final 状态的消息，避免流式返回导致重复
        if state and state != "final":
            # 尝试提取流式文本内容
            text = self._extract_text(payload.get("message"))
            if text and self.on_message:
                # 有文本内容，传递流式增量给 UI
                self.on_message("__stream__", text)
            elif self.on_message:
                # 没有文本，只是思考状态通知
                self.on_message("__thinking__", "thinking")
            return

        session_key = str(payload.get("sessionKey", ""))
        raw_session_key = self.employee.session_key or self.employee.config.get("session_key")
        if not raw_session_key and self.employee.agent_id:
            raw_session_key = f"agent:{self.employee.agent_id}:main"
        expected = self._normalize_chat_session_key(raw_session_key or self.employee.name.lower())
        if session_key and expected and session_key != expected:
            logger.debug(f"[{self.employee.id}] Session key mismatch: {session_key} != {expected}")
            return

        task_id = ""
        for key in ("idempotencyKey", "taskId", "id"):
            val = payload.get(key)
            if isinstance(val, str) and val:
                task_id = val
                break

        text = self._extract_text(payload.get("message"))
        logger.debug(f"[{self.employee.id}] Chat text: {text[:100]}...")

        if self.on_message and text:
            self.on_message(self.employee.name, text)

        if task_id and task_id in self._task_waiters:
            fut = self._task_waiters.get(task_id)
            if fut and not fut.done():
                fut.set_result(text)
            return

        if len(self._task_waiters) == 1:
            _, fut = next(iter(self._task_waiters.items()))
            if fut and not fut.done():
                fut.set_result(text)

    def _extract_text(self, message: Any) -> str:
        """从消息中提取文本"""
        if isinstance(message, str):
            return message.strip()

        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts: list[str] = []
                for part in content:
                    if isinstance(part, dict):
                        txt = part.get("text") or part.get("content") or ""
                        if isinstance(txt, str):
                            parts.append(txt)
                    elif isinstance(part, str):
                        parts.append(part)
                return "".join(parts).strip()
            if isinstance(message.get("text"), str):
                return str(message.get("text", "")).strip()
            if "message" in message:
                return self._extract_text(message.get("message"))

        if isinstance(message, list):
            parts = []
            for item in message:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    txt = item.get("text") or item.get("content") or ""
                    if isinstance(txt, str):
                        parts.append(txt)
            return "".join(parts).strip()

        return ""

    def _update_status(self, status: str):
        """更新员工状态"""
        if self._closed:
            return
        old_status = self.employee.status
        self.employee.status = status
        logger.debug(f"[{self.employee.id}] Status: {old_status} -> {status}")
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception as e:
                logger.warning(f"[{self.employee.id}] Status change callback error: {e}")

    def _wake_all_waiters(self, exc: Exception):
        """唤醒所有等待的 future"""
        for fut in list(self._rpc_waiters.values()):
            if not fut.done():
                fut.set_exception(exc)
        for fut in list(self._task_waiters.values()):
            if not fut.done():
                fut.set_exception(exc)

    @staticmethod
    def _normalize_chat_session_key(session_key: str) -> str:
        """标准化 session key"""
        key = (session_key or "").strip()
        if not key:
            return "agent:main:main"
        if ":" in key:
            return key
        return f"agent:main:{key}"

    async def close(self):
        """关闭连接"""
        logger.info(f"[{self.employee.id}] Closing connection")
        self._closed = True
        
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except Exception:
                pass

        if self._ws and not self._ws.closed:
            await self._ws.close()

        if self._session and not self._session.closed:
            await self._session.close()

        self._ws = None
        self._session = None
        self._recv_task = None
        self._connected = False
        self.employee.status = "offline"

        self._wake_all_waiters(RuntimeError("OpenClaw client closed"))
        logger.debug(f"[{self.employee.id}] Connection closed")
