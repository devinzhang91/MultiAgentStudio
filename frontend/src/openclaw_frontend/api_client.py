"""后端 API 客户端"""
import asyncio
import json
from typing import Optional, Callable, List, Dict, Any
import httpx
import websockets


class BackendClient:
    """连接到后端服务的客户端"""
    
    def __init__(self, api_url: str = "http://localhost:18765", ws_url: str = "ws://localhost:18765/ws"):
        self.api_url = api_url
        self.ws_url = ws_url
        self.http_client = httpx.AsyncClient(base_url=api_url, timeout=10.0)
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self._callbacks: Dict[str, List[Callable]] = {}
        self._ws_task: Optional[asyncio.Task] = None
    
    def on(self, event_type: str, callback: Callable):
        """注册事件回调"""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)
    
    def _trigger(self, event_type: str, data: Any):
        """触发事件回调"""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                print(f"[Client] 回调错误: {e}")
    
    # ========== HTTP API ==========
    
    async def get(self, path: str) -> Dict:
        resp = await self.http_client.get(path)
        resp.raise_for_status()
        return resp.json()
    
    async def post(self, path: str, json: Dict = None) -> Dict:
        resp = await self.http_client.post(path, json=json)
        resp.raise_for_status()
        return resp.json()
    
    async def delete(self, path: str) -> Dict:
        resp = await self.http_client.delete(path)
        resp.raise_for_status()
        return resp.json()
    
    async def get_employees(self) -> List[Dict]:
        """获取员工列表"""
        try:
            resp = await self.http_client.get("/api/employees")
            resp.raise_for_status()
            data = resp.json()
            return data.get("employees", [])
        except Exception as e:
            print(f"[Client] 获取员工失败: {e}")
            return []
    
    async def get_employee(self, employee_id: str) -> Optional[Dict]:
        """获取单个员工"""
        try:
            resp = await self.http_client.get(f"/api/employees/{employee_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None
    
    async def get_messages(self, employee_id: str) -> List[Dict]:
        """获取消息历史"""
        try:
            resp = await self.http_client.get(f"/api/employees/{employee_id}/messages")
            resp.raise_for_status()
            data = resp.json()
            return data.get("messages", [])
        except Exception as e:
            print(f"[Client] 获取消息失败: {e}")
            return []
    
    async def send_message(self, employee_id: str, content: str) -> Optional[Dict]:
        """发送消息"""
        try:
            resp = await self.http_client.post(
                f"/api/employees/{employee_id}/messages",
                json={"content": content}
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[Client] 发送消息失败: {e}")
            raise
    
    # ========== WebSocket ==========
    
    async def connect_websocket(self):
        """建立 WebSocket 连接"""
        self._ws_task = asyncio.create_task(self._ws_loop())
    
    async def _ws_loop(self):
        """WebSocket 连接循环"""
        while True:
            try:
                print(f"[Client] 连接 WebSocket: {self.ws_url}")
                async with websockets.connect(self.ws_url) as ws:
                    self.websocket = ws
                    self.connected = True
                    print("[Client] WebSocket 连接成功")
                    
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            msg_type = data.get("type")
                            
                            if msg_type == "init":
                                self._trigger("init", data.get("employees", []))
                            elif msg_type == "employee_created":
                                self._trigger("employee_created", data)
                            elif msg_type == "employee_updated":
                                self._trigger("employee_updated", data)
                            elif msg_type == "employee_deleted":
                                self._trigger("employee_deleted", data)
                            elif msg_type == "employee_status_changed":
                                self._trigger("employee_status_changed", data)
                            elif msg_type == "new_message":
                                self._trigger("new_message", data)
                                
                        except json.JSONDecodeError:
                            pass
                            
            except websockets.exceptions.ConnectionClosed:
                print("[Client] WebSocket 断开")
            except Exception as e:
                print(f"[Client] WebSocket 错误: {e}")
            
            self.connected = False
            await asyncio.sleep(3)
    
    async def close(self):
        """关闭连接"""
        if self._ws_task:
            self._ws_task.cancel()
        if self.websocket:
            await self.websocket.close()
        await self.http_client.aclose()
