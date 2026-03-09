"""OpenClaw WebSocket 客户端 - 与 OpenClaw 保持长连接"""
import asyncio
import json
import websockets
from typing import Callable, Optional
from datetime import datetime


class OpenClawWebSocketClient:
    """与 OpenClaw 的 WebSocket 长连接客户端"""
    
    def __init__(self, ws_url: str, api_key: str):
        self.ws_url = ws_url
        self.api_key = api_key
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self._running = False
        self._callbacks: list[Callable] = []
        self._reconnect_interval = 5  # 重连间隔（秒）
    
    def on_message(self, callback: Callable):
        """注册消息回调"""
        self._callbacks.append(callback)
    
    async def connect(self):
        """建立 WebSocket 连接"""
        self._running = True
        while self._running:
            try:
                print(f"[OpenClaw] 连接到 {self.ws_url}...")
                
                headers = {"Authorization": f"Bearer {self.api_key}"}
                self.websocket = await websockets.connect(
                    self.ws_url,
                    extra_headers=headers
                )
                
                self.connected = True
                print("[OpenClaw] WebSocket 连接成功")
                
                # 发送认证消息
                await self.send({
                    "type": "auth",
                    "api_key": self.api_key
                })
                
                # 接收消息循环
                await self._receive_loop()
                
            except websockets.exceptions.ConnectionClosed:
                print("[OpenClaw] 连接断开，准备重连...")
            except Exception as e:
                print(f"[OpenClaw] 连接错误: {e}")
            
            self.connected = False
            
            if self._running:
                print(f"[OpenClaw] {self._reconnect_interval}秒后重连...")
                await asyncio.sleep(self._reconnect_interval)
    
    async def _receive_loop(self):
        """接收消息循环"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    print(f"[OpenClaw] 收到消息: {data}")
                    
                    # 通知所有回调
                    for callback in self._callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            print(f"[OpenClaw] 回调错误: {e}")
                            
                except json.JSONDecodeError:
                    print(f"[OpenClaw] 收到非 JSON 消息: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("[OpenClaw] 连接已关闭")
    
    async def send(self, data: dict):
        """发送消息到 OpenClaw"""
        if self.websocket and self.connected:
            await self.websocket.send(json.dumps(data))
    
    async def send_task(self, employee_id: str, content: str):
        """发送任务给员工"""
        await self.send({
            "type": "task.assign",
            "employee_id": employee_id,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    async def close(self):
        """关闭连接"""
        self._running = False
        if self.websocket:
            await self.websocket.close()
            self.connected = False
