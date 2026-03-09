"""
OpenClaw Backend Server
员工管理 + OpenClaw 连接管理
"""
import asyncio
import json
import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .employee_model import Employee, OpenClawConfig, employee_store, EmployeeStatus
from .openclaw_service import openclaw_manager

# 配置
API_PORT = 18765

# WebSocket 连接管理器
class ConnectionManager:
    """管理前端 WebSocket 连接"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[Backend] 前端连接，当前: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """广播消息给所有前端"""
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.append(conn)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# ========== Pydantic Models ==========

class OpenClawConfigSchema(BaseModel):
    base_url: str = ""
    token: str = ""
    session_key: str = "default"
    timeout: int = 120
    enabled: bool = True

class EmployeeCreate(BaseModel):
    name: str
    role: str = "OpenClaw 员工"
    config: OpenClawConfigSchema

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    config: Optional[OpenClawConfigSchema] = None

class SendMessageRequest(BaseModel):
    content: str

class UpdateStatusRequest(BaseModel):
    status: str
    task: Optional[str] = None

# ========== Lifecycle ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    print("[Backend] 启动 OpenClaw Backend...")
    
    # 启动所有启用员工的 OpenClaw 连接
    for emp in employee_store.get_all():
        if emp.config.enabled and emp.config.base_url:
            asyncio.create_task(openclaw_manager.start_employee(emp))
    
    yield
    
    # 关闭时
    print("[Backend] 关闭服务器...")
    await openclaw_manager.stop_all()

app = FastAPI(
    title="OpenClaw Backend",
    version="0.2.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== REST API - Employees ==========

@app.get("/")
async def root():
    return {"message": "OpenClaw Backend API", "version": "0.2.0"}

@app.get("/api/employees")
async def get_employees():
    """获取所有员工列表"""
    return {
        "employees": [e.to_dict() for e in employee_store.get_all()]
    }

@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: str):
    """获取单个员工"""
    emp = employee_store.get(employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    return emp.to_dict()

@app.post("/api/employees")
async def create_employee(req: EmployeeCreate):
    """创建新员工"""
    import uuid
    
    emp = Employee(
        id=f"emp-{uuid.uuid4().hex[:8]}",
        name=req.name,
        role=req.role,
        config=OpenClawConfig(
            base_url=req.config.base_url,
            token=req.config.token,
            session_key=req.config.session_key,
            timeout=req.config.timeout,
            enabled=req.config.enabled,
        )
    )
    
    employee_store.create(emp)
    
    # 如果启用，启动 OpenClaw 连接
    if emp.config.enabled and emp.config.base_url:
        asyncio.create_task(openclaw_manager.start_employee(emp))
    
    await manager.broadcast({
        "type": "employee_created",
        "employee": emp.to_dict()
    })
    
    return emp.to_dict()

@app.put("/api/employees/{employee_id}")
async def update_employee(employee_id: str, req: EmployeeUpdate):
    """更新员工"""
    emp = employee_store.get(employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    
    update_data = {}
    if req.name is not None:
        update_data["name"] = req.name
    if req.role is not None:
        update_data["role"] = req.role
    if req.config is not None:
        update_data["config"] = req.config.dict()
    
    updated = employee_store.update(employee_id, **update_data)
    
    # 如果配置改变，重启连接
    if req.config is not None and emp.config.enabled:
        await openclaw_manager.restart_employee(updated)
    
    await manager.broadcast({
        "type": "employee_updated",
        "employee": updated.to_dict()
    })
    
    return updated.to_dict()

@app.delete("/api/employees/{employee_id}")
async def delete_employee(employee_id: str):
    """删除员工"""
    emp = employee_store.get(employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    
    # 停止连接
    await openclaw_manager.stop_employee(employee_id)
    
    # 删除数据
    employee_store.delete(employee_id)
    
    await manager.broadcast({
        "type": "employee_deleted",
        "employee_id": employee_id
    })
    
    return {"success": True}

@app.post("/api/employees/{employee_id}/restart")
async def restart_employee_connection(employee_id: str):
    """重启员工的 OpenClaw 连接"""
    emp = employee_store.get(employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    
    await openclaw_manager.restart_employee(emp)
    return {"success": True, "message": "Connection restarted"}

# ========== REST API - Messages & Status ==========

@app.get("/api/employees/{employee_id}/messages")
async def get_messages(employee_id: str):
    """获取消息历史"""
    emp = employee_store.get(employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    
    messages = employee_store.get_messages(employee_id)
    employee_store.clear_unread(employee_id)
    
    return {"messages": messages}

@app.post("/api/employees/{employee_id}/messages")
async def send_message(employee_id: str, req: SendMessageRequest):
    """发送消息给员工"""
    emp = employee_store.get(employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    
    # 保存用户消息
    user_msg = employee_store.add_message(employee_id, req.content, is_user=True)
    
    # 发送到 OpenClaw
    response_text = await openclaw_manager.send_message(employee_id, req.content)
    
    # 保存回复
    if response_text:
        bot_msg = employee_store.add_message(employee_id, response_text, is_user=False)
        
        # 广播给前端
        await manager.broadcast({
            "type": "new_message",
            "employee_id": employee_id,
            "message": bot_msg
        })
    
    return user_msg

@app.post("/api/employees/{employee_id}/status")
async def update_status(employee_id: str, req: UpdateStatusRequest):
    """更新员工状态"""
    emp = employee_store.get(employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    
    employee_store.update_status(employee_id, req.status, req.task)
    
    await manager.broadcast({
        "type": "employee_status_changed",
        "employee_id": employee_id,
        "status": req.status,
        "current_task": req.task
    })
    
    return {"success": True}

# ========== WebSocket ==========

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """前端 WebSocket 连接"""
    await manager.connect(websocket)
    
    try:
        # 发送初始数据
        await websocket.send_json({
            "type": "init",
            "employees": [e.to_dict() for e in employee_store.get_all()]
        })
        
        # 接收消息
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "restart_connection":
                    emp_id = msg.get("employee_id")
                    if emp_id:
                        emp = employee_store.get(emp_id)
                        if emp:
                            await openclaw_manager.restart_employee(emp)
                            
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[Backend] WebSocket 错误: {e}")
        manager.disconnect(websocket)

def main():
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🦞 OpenClaw Backend Server v0.2.0                       ║
║                                                           ║
║   API: http://localhost:{API_PORT}                          ║
║   WebSocket: ws://localhost:{API_PORT}/ws                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT, log_level="info")

if __name__ == "__main__":
    main()
