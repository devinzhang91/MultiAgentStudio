"""OpenClaw Webhook 客户端"""
import asyncio
import hashlib
import hmac
import json
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import httpx

from .models import Employee, Task, Message, EmployeeStatus, TaskStatus


class OpenClawClient:
    """OpenClaw Webhook 客户端
    
    负责与 OpenClaw API 进行双向通信：
    - 发送任务/消息到 OpenClaw (Outgoing Webhook)
    - 接收状态更新回调 (Incoming Webhook)
    """
    
    def __init__(
        self,
        api_base: str,
        api_key: str,
        webhook_send_url: str,
        webhook_secret: str,
        webhook_receive_port: int = 8765,
        webhook_receive_path: str = "/webhook",
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.webhook_send_url = webhook_send_url
        self.webhook_secret = webhook_secret
        self.webhook_receive_port = webhook_receive_port
        self.webhook_receive_path = webhook_receive_path
        
        # HTTP 客户端
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0
        )
        
        # 回调处理器
        self._status_callbacks: list[Callable] = []
        self._message_callbacks: list[Callable] = []
        self._task_callbacks: list[Callable] = []
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()
    
    async def get_employees(self) -> list[Employee]:
        """获取员工列表"""
        try:
            response = await self._client.get(
                f"{self.api_base}/v1/employees"
            )
            response.raise_for_status()
            data = response.json()
            return [Employee.from_dict(e) for e in data.get("employees", [])]
        except Exception as e:
            print(f"获取员工列表失败: {e}")
            return []
    
    async def send_task(self, employee_id: str, content: str) -> Optional[Task]:
        """发送任务给员工"""
        try:
            payload = {
                "event": "task.assign",
                "employee_id": employee_id,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
            
            # 签名请求
            signature = self._sign_payload(payload)
            
            response = await self._client.post(
                self.webhook_send_url,
                json=payload,
                headers={"X-Webhook-Signature": signature}
            )
            response.raise_for_status()
            
            result = response.json()
            return Task(
                id=result.get("task_id", ""),
                employee_id=employee_id,
                content=content,
                status=TaskStatus.PENDING,
            )
        except Exception as e:
            print(f"发送任务失败: {e}")
            return None
    
    async def send_message(self, employee_id: str, content: str) -> Optional[Message]:
        """发送消息给员工"""
        try:
            payload = {
                "event": "message.send",
                "employee_id": employee_id,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
            
            signature = self._sign_payload(payload)
            
            response = await self._client.post(
                self.webhook_send_url,
                json=payload,
                headers={"X-Webhook-Signature": signature}
            )
            response.raise_for_status()
            
            result = response.json()
            return Message(
                id=result.get("message_id", ""),
                employee_id=employee_id,
                content=content,
                is_user=True,
            )
        except Exception as e:
            print(f"发送消息失败: {e}")
            return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            payload = {
                "event": "task.cancel",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat(),
            }
            
            signature = self._sign_payload(payload)
            
            response = await self._client.post(
                self.webhook_send_url,
                json=payload,
                headers={"X-Webhook-Signature": signature}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"取消任务失败: {e}")
            return False
    
    async def query_employee_status(self, employee_id: str) -> Optional[Employee]:
        """查询员工状态"""
        try:
            payload = {
                "event": "employee.query",
                "employee_id": employee_id,
                "timestamp": datetime.now().isoformat(),
            }
            
            signature = self._sign_payload(payload)
            
            response = await self._client.post(
                self.webhook_send_url,
                json=payload,
                headers={"X-Webhook-Signature": signature}
            )
            response.raise_for_status()
            
            result = response.json()
            return Employee.from_dict(result.get("employee", {}))
        except Exception as e:
            print(f"查询员工状态失败: {e}")
            return None
    
    def _sign_payload(self, payload: dict) -> str:
        """为请求体生成签名"""
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.webhook_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """验证 webhook 回调签名"""
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)
    
    # 回调注册
    def on_status_update(self, callback: Callable):
        """注册状态更新回调"""
        self._status_callbacks.append(callback)
    
    def on_message_received(self, callback: Callable):
        """注册消息接收回调"""
        self._message_callbacks.append(callback)
    
    def on_task_event(self, callback: Callable):
        """注册任务事件回调"""
        self._task_callbacks.append(callback)
    
    # 事件触发
    def handle_incoming_webhook(self, event_type: str, data: dict):
        """处理接收到的 webhook 事件"""
        if event_type == "status.update":
            for cb in self._status_callbacks:
                cb(data)
        elif event_type == "message.receive":
            for cb in self._message_callbacks:
                cb(data)
        elif event_type in ("task.complete", "progress.report", "error.report"):
            for cb in self._task_callbacks:
                cb(event_type, data)
