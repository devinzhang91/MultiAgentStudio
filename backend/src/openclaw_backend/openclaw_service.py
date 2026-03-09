"""
OpenClaw Service - 员工级 WebSocket 连接
基于 live2d-ai-assistant 的 OpenClawService 简化版
"""
import asyncio
import base64
import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional, Callable
from urllib.parse import urlparse

import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .employee_model import Employee, EmployeeStatus, employee_store


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


class EmployeeOpenClawService:
    """
    单个员工的 OpenClaw 连接服务
    每个员工有独立的 WebSocket 连接
    """
    
    def __init__(self, employee: Employee):
        self.employee = employee
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._recv_task: Optional[asyncio.Task] = None
        self._conn_lock = asyncio.Lock()
        
        self._rpc_waiters: dict[str, asyncio.Future] = {}
        self._task_waiters: dict[str, asyncio.Future] = {}
        
        self._connect_nonce: str = ""
        self._hello_ok = asyncio.Event()
        
        self._connected = False
        self._running = False
        
        # Device identity
        self._device_id = ""
        self._device_public_key_raw_b64url = ""
        self._device_private_key: Optional[Ed25519PrivateKey] = None
        
        # Callbacks
        self._on_message: Optional[Callable[[str], None]] = None
        self._on_status_change: Optional[Callable[[str, str], None]] = None
    
    def set_callbacks(self, on_message: Callable = None, on_status_change: Callable = None):
        """设置回调"""
        self._on_message = on_message
        self._on_status_change = on_status_change
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws and not self._ws.closed
    
    async def start(self):
        """启动连接（后台运行）"""
        if not self.employee.config.enabled or not self.employee.config.base_url:
            print(f"[{self.employee.name}] OpenClaw 未启用或未配置 base_url")
            return
        
        self._running = True
        while self._running:
            try:
                await self._connect()
                # 连接成功后保持运行
                while self._running and self.is_connected:
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"[{self.employee.name}] 连接错误: {e}")
            
            self._connected = False
            employee_store.update_status(
                self.employee.id, 
                "offline", 
                error="连接断开" if self._running else None
            )
            
            if self._running:
                print(f"[{self.employee.name}] 5秒后重连...")
                await asyncio.sleep(5)
    
    async def stop(self):
        """停止连接"""
        self._running = False
        await self.close()
    
    async def send_message(self, content: str) -> Optional[str]:
        """发送消息并等待回复"""
        if not self.is_connected:
            # 尝试连接
            try:
                await self._connect()
            except Exception as e:
                return f"❌ 连接失败: {e}"
        
        try:
            return await self._send_chat_and_wait(content)
        except asyncio.TimeoutError:
            return f"⏳ 请求超时（>{self.employee.config.timeout}s）"
        except Exception as e:
            return f"❌ 发送失败: {e}"
    
    async def _connect(self):
        """建立连接"""
        async with self._conn_lock:
            if self._connected:
                return
            
            self._load_or_create_identity()
            
            base_url = self.employee.config.base_url
            parsed = urlparse(base_url)
            scheme = "wss" if parsed.scheme == "https" else "ws"
            ws_url = f"{scheme}://{parsed.netloc}"
            origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else None
            
            print(f"[{self.employee.name}] 连接到 {ws_url}...")
            
            headers = {"Origin": origin} if origin else {}
            self._session = aiohttp.ClientSession()
            self._ws = await self._session.ws_connect(
                ws_url,
                headers=headers,
                heartbeat=30,
            )
            
            self._connect_nonce = ""
            self._hello_ok.clear()
            self._recv_task = asyncio.create_task(self._recv_loop())
            
            await self._wait_for_challenge(timeout=10)
            await self._do_handshake(timeout=15)
            
            self._connected = True
            employee_store.update_status(self.employee.id, "idle")
            print(f"[{self.employee.name}] 已连接")
    
    async def close(self):
        """关闭连接"""
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
        
        self._wake_all_waiters(RuntimeError("连接已关闭"))
    
    def _load_or_create_identity(self):
        """加载或创建设备身份"""
        # 每个员工独立的 identity 文件
        identity_dir = Path.home() / ".openclaw_tui" / "identities"
        identity_dir.mkdir(parents=True, exist_ok=True)
        path = identity_dir / f"{self.employee.id}.json"
        
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
                        return
            except Exception as exc:
                print(f"[{self.employee.name}] 读取 identity 失败: {exc}")
        
        # 创建新的 identity
        private_key = Ed25519PrivateKey.generate()
        public_key_raw = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        device_id = hashlib.sha256(public_key_raw).hexdigest()
        
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        
        data = {
            "version": 1,
            "device_id": device_id,
            "private_key_pem": private_key_pem,
            "created_at_ms": _now_ms(),
        }
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        
        self._device_private_key = private_key
        self._device_id = device_id
        self._device_public_key_raw_b64url = _b64url(public_key_raw)
    
    async def _wait_for_challenge(self, timeout: float):
        """等待 challenge"""
        deadline = time.monotonic() + timeout
        while not self._connect_nonce:
            if time.monotonic() > deadline:
                raise TimeoutError("connect.challenge timeout")
            await asyncio.sleep(0.05)
    
    async def _do_handshake(self, timeout: float):
        """执行握手"""
        scopes = ["operator.chat"]
        client_id = f"openclaw-tui-{self.employee.id}"
        
        params = {
            "minProtocol": 3,
            "maxProtocol": 3,
            "client": {
                "id": client_id,
                "version": "0.1.0",
                "platform": "openclaw-tui-studio",
                "mode": "ui",
                "instanceId": self.employee.id,
            },
            "role": "operator",
            "scopes": scopes,
            "locale": "zh-CN",
            "device": self._build_device_payload(scopes),
        }
        
        if self.employee.config.token:
            params["auth"] = {"token": self.employee.config.token}
        
        res = await self._rpc("connect", params=params, timeout_s=timeout)
        if isinstance(res, dict) and res.get("type") == "hello-ok":
            self._hello_ok.set()
        
        await asyncio.wait_for(self._hello_ok.wait(), timeout=timeout)
    
    def _build_device_payload(self, scopes: list) -> dict:
        """构建设备 payload"""
        if not self._device_private_key:
            raise RuntimeError("Device identity not loaded")
        
        signed_at_ms = _now_ms()
        payload = "|".join([
            "v2",
            self._device_id,
            f"openclaw-tui-{self.employee.id}",
            "ui",
            "operator",
            ",".join(scopes),
            str(signed_at_ms),
            self.employee.config.token or "",
            self._connect_nonce,
        ])
        
        signature = self._device_private_key.sign(payload.encode("utf-8"))
        return {
            "id": self._device_id,
            "publicKey": self._device_public_key_raw_b64url,
            "signature": _b64url(signature),
            "signedAt": signed_at_ms,
            "nonce": self._connect_nonce,
        }
    
    async def _send_chat_and_wait(self, message: str) -> str:
        """发送聊天消息并等待回复"""
        task_id = str(uuid.uuid4())
        fut = asyncio.get_running_loop().create_future()
        self._task_waiters[task_id] = fut
        
        payload = {
            "sessionKey": self._normalize_session_key(self.employee.config.session_key),
            "message": message,
            "deliver": False,
            "idempotencyKey": task_id,
        }
        
        try:
            # 更新状态为工作中
            employee_store.update_status(self.employee.id, "working", task="处理中...")
            if self._on_status_change:
                self._on_status_change("working", "处理中...")
            
            await self._rpc("chat.send", params=payload, timeout_s=15)
            result = await asyncio.wait_for(fut, timeout=self.employee.config.timeout)
            
            # 恢复空闲状态
            employee_store.update_status(self.employee.id, "idle", task="")
            if self._on_status_change:
                self._on_status_change("idle", "")
            
            return str(result)
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
        await self._ws.send_str(json.dumps(frame, ensure_ascii=False))
        
        try:
            return await asyncio.wait_for(fut, timeout=timeout_s)
        finally:
            self._rpc_waiters.pop(req_id, None)
    
    async def _recv_loop(self):
        """接收消息循环"""
        try:
            async for msg in self._ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                await self._handle_frame(str(msg.data))
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            print(f"[{self.employee.name}] 接收错误: {exc}")
        finally:
            self._connected = False
    
    async def _handle_frame(self, raw: str):
        """处理收到的帧"""
        try:
            frame = json.loads(raw)
        except Exception:
            return
        
        frame_type = frame.get("type")
        
        if frame_type == "res":
            req_id = str(frame.get("id", ""))
            fut = self._rpc_waiters.get(req_id)
            if fut and not fut.done():
                if frame.get("ok"):
                    fut.set_result(frame.get("payload"))
                else:
                    err = frame.get("error")
                    fut.set_exception(RuntimeError(str(err) if err else "rpc failed"))
            return
        
        if frame_type == "event":
            event = frame.get("event")
            payload = frame.get("payload")
            
            if event == "connect.challenge" and isinstance(payload, dict):
                self._connect_nonce = str(payload.get("nonce", "")).strip()
                return
            
            if event == "chat" and isinstance(payload, dict):
                await self._handle_chat_event(payload)
                return
        
        if frame_type == "hello-ok":
            self._hello_ok.set()
    
    async def _handle_chat_event(self, payload: dict):
        """处理聊天事件"""
        state = payload.get("state")
        if state and state != "final":
            return
        
        task_id = ""
        for key in ("idempotencyKey", "taskId", "id"):
            val = payload.get(key)
            if isinstance(val, str) and val:
                task_id = val
                break
        
        text = self._extract_text(payload.get("message"))
        
        if task_id and task_id in self._task_waiters:
            fut = self._task_waiters.get(task_id)
            if fut and not fut.done():
                fut.set_result(text)
        
        # 通知回调
        if self._on_message:
            self._on_message(text)
    
    def _extract_text(self, message: Any) -> str:
        """提取文本"""
        if isinstance(message, str):
            return message.strip()
        
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict):
                        txt = part.get("text") or part.get("content") or ""
                        if isinstance(txt, str):
                            parts.append(txt)
                    elif isinstance(part, str):
                        parts.append(part)
                return "".join(parts).strip()
        
        return ""
    
    def _wake_all_waiters(self, exc: Exception):
        """唤醒所有等待者"""
        for fut in list(self._rpc_waiters.values()):
            if not fut.done():
                fut.set_exception(exc)
        for fut in list(self._task_waiters.values()):
            if not fut.done():
                fut.set_exception(exc)
    
    @staticmethod
    def _normalize_session_key(session_key: str) -> str:
        key = (session_key or "").strip()
        if not key:
            return "agent:main:main"
        if ":" in key:
            return key
        return f"agent:main:{key}"


class OpenClawManager:
    """管理所有员工的 OpenClaw 连接"""
    
    def __init__(self):
        self._services: dict[str, EmployeeOpenClawService] = {}
        self._tasks: dict[str, asyncio.Task] = {}
    
    async def start_employee(self, employee: Employee):
        """启动员工的连接"""
        if employee.id in self._services:
            return
        
        service = EmployeeOpenClawService(employee)
        self._services[employee.id] = service
        
        # 启动后台任务
        task = asyncio.create_task(service.start())
        self._tasks[employee.id] = task
    
    async def stop_employee(self, employee_id: str):
        """停止员工的连接"""
        service = self._services.pop(employee_id, None)
        if service:
            await service.stop()
        
        task = self._tasks.pop(employee_id, None)
        if task and not task.done():
            task.cancel()
    
    async def restart_employee(self, employee: Employee):
        """重启员工的连接"""
        await self.stop_employee(employee.id)
        await asyncio.sleep(1)
        await self.start_employee(employee)
    
    async def send_message(self, employee_id: str, content: str) -> str:
        """发送消息"""
        service = self._services.get(employee_id)
        if not service:
            return "❌ 员工未连接"
        return await service.send_message(content)
    
    async def stop_all(self):
        """停止所有连接"""
        for emp_id in list(self._services.keys()):
            await self.stop_employee(emp_id)


# 全局管理器
openclaw_manager = OpenClawManager()
