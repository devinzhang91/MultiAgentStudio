"""
OpenClaw Backend Server
提供 REST API 和 WebSocket 给前端
"""
import asyncio
import json
import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import store, Employee, Message
from .openclaw_client import OpenClawWebSocketClient

# 配置
API_PORT = 18765
WS_PORT = 18766

# OpenClaw 配置（演示模式为空）
OPENCLAW_WS_URL = ""  # "wss://api.openclaw.ai/ws"
OPENCLAW_API_KEY = ""

# OpenClaw 客户端
openclaw_client: Optional[OpenClawWebSocketClient] = None

# WebSocket 连接管理器
class ConnectionManager:
    """管理前端 WebSocket 连接"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[Backend] 前端连接建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"[Backend] 前端连接断开，当前连接数: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """广播消息给所有前端"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[Backend] 发送失败: {e}")

manager = ConnectionManager()

# 请求模型
class SendMessageRequest(BaseModel):
    content: str

class UpdateStatusRequest(BaseModel):
    status: str
    task: Optional[str] = None

# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    global openclaw_client
    
    # 启动时
    print("[Backend] 启动 OpenClaw Backend Server...")
    
    # 连接 OpenClaw（如果配置了）
    if OPENCLAW_WS_URL and OPENCLAW_API_KEY:
        openclaw_client = OpenClawWebSocketClient(OPENCLAW_WS_URL, OPENCLAW_API_KEY)
        openclaw_client.on_message(handle_openclaw_message)
        asyncio.create_task(openclaw_client.connect())
    else:
        print("[Backend] 演示模式: 未配置 OpenClaw WebSocket")
    
    yield
    
    # 关闭时
    print("[Backend] 关闭服务器...")
    if openclaw_client:
        await openclaw_client.close()

# 创建 FastAPI 应用
app = FastAPI(
    title="OpenClaw Backend",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def handle_openclaw_message(data: dict):
    """处理来自 OpenClaw 的消息"""
    msg_type = data.get("type")
    
    if msg_type == "status.update":
        employee_id = data.get("employee_id")
        status = data.get("status")
        task = data.get("current_task")
        store.update_employee_status(employee_id, status, task)
        
        # 广播给前端
        asyncio.create_task(manager.broadcast({
            "type": "employee_status_changed",
            "employee_id": employee_id,
            "status": status,
            "current_task": task
        }))
    
    elif msg_type == "message":
        employee_id = data.get("employee_id")
        content = data.get("content")
        msg = store.add_message(employee_id, content, is_user=False)
        
        # 广播给前端
        asyncio.create_task(manager.broadcast({
            "type": "new_message",
            "employee_id": employee_id,
            "message": msg.to_dict()
        }))

# ========== REST API ==========

@app.get("/")
async def root():
    return {"message": "OpenClaw Backend API", "version": "0.1.0"}

@app.get("/api/employees")
async def get_employees():
    """获取所有员工列表"""
    return {
        "employees": [e.to_dict() for e in store.get_employees()]
    }

@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: str):
    """获取单个员工信息"""
    emp = store.get_employee(employee_id)
    if not emp:
        return {"error": "Employee not found"}, 404
    return emp.to_dict()

@app.post("/api/employees/{employee_id}/status")
async def update_employee_status(employee_id: str, req: UpdateStatusRequest):
    """更新员工状态"""
    store.update_employee_status(employee_id, req.status, req.task)
    
    # 广播更新
    await manager.broadcast({
        "type": "employee_status_changed",
        "employee_id": employee_id,
        "status": req.status,
        "current_task": req.task
    })
    
    return {"success": True}

@app.get("/api/employees/{employee_id}/messages")
async def get_messages(employee_id: str):
    """获取与员工的消息历史"""
    messages = store.get_messages(employee_id)
    
    # 清除未读
    store.clear_unread(employee_id)
    
    return {
        "messages": [m.to_dict() for m in messages]
    }

@app.post("/api/employees/{employee_id}/messages")
async def send_message(employee_id: str, req: SendMessageRequest):
    """发送消息给员工"""
    # 保存用户消息
    user_msg = store.add_message(employee_id, req.content, is_user=True)
    
    # 发送到 OpenClaw（如果已连接）
    if openclaw_client and openclaw_client.connected:
        await openclaw_client.send_task(employee_id, req.content)
    else:
        # 演示模式：模拟响应
        asyncio.create_task(simulate_response(employee_id, req.content))
    
    return user_msg.to_dict()

async def simulate_response(employee_id: str, content: str):
    """演示模式：模拟员工响应"""
    await asyncio.sleep(1.5)
    
    emp = store.get_employee(employee_id)
    if not emp:
        return
    
    responses = {
        "alice-001": f"✅ 收到！我是 {emp.name}，正在分析代码...",
        "bob-002": f"📝 {emp.name} 开始生成文档，请稍等。",
        "carol-003": f"🧪 {emp.name} 准备执行测试。",
        "dave-004": "⚫ 抱歉，我当前离线。",
        "eve-005": f"📊 {emp.name} 正在处理数据分析...",
    }
    
    response = responses.get(
        employee_id,
        f"🦞 {emp.name} 收到: {content[:20]}..."
    )
    
    # 添加响应消息
    msg = store.add_message(employee_id, response, is_user=False)
    
    # 广播给前端
    await manager.broadcast({
        "type": "new_message",
        "employee_id": employee_id,
        "message": msg.to_dict()
    })

# ========== WebSocket ==========

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """前端 WebSocket 连接"""
    await manager.connect(websocket)
    
    try:
        # 发送初始数据
        await websocket.send_json({
            "type": "init",
            "employees": [e.to_dict() for e in store.get_employees()]
        })
        
        # 接收消息
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                print(f"[Backend] 收到前端消息: {msg}")
                
                # 处理前端命令
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except json.JSONDecodeError:
                print(f"[Backend] 收到无效消息: {data}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[Backend] WebSocket 错误: {e}")
        manager.disconnect(websocket)

def main():
    """启动服务器"""
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🦞 OpenClaw Backend Server                              ║
║                                                           ║
║   REST API: http://localhost:{API_PORT}                     ║
║   WebSocket: ws://localhost:{API_PORT}/ws                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT, log_level="info")

if __name__ == "__main__":
    main()
