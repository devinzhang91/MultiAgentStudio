# OpenClaw TUI Studio 架构说明

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户终端                                  │
│  ┌─────────────────────┐         ┌─────────────────────────────┐ │
│  │   TUI 前端           │◄───────►│      后端服务               │ │
│  │   (Frontend)        │  HTTP   │     (Backend)              │ │
│  │                     │  WS     │                            │ │
│  │  - 纯展示交互       │         │  - 与 OpenClaw WebSocket   │ │
│  │  - 可重复打开/关闭  │         │  - 数据存储                │ │
│  │  - 无状态           │         │  - API 服务                │ │
│  └─────────────────────┘         └──────────────┬──────────────┘ │
│                                                 │                │
└─────────────────────────────────────────────────┼────────────────┘
                                                  │
                                                  ▼ WebSocket
                                    ┌─────────────────────────────┐
                                    │     OpenClaw 服务           │
                                    │     (外部 API)              │
                                    └─────────────────────────────┘
```

## 📁 目录结构

```
openclaw-tui-studio/
├── backend/                      # 后端服务
│   ├── src/openclaw_backend/
│   │   ├── __init__.py
│   │   ├── server.py            # FastAPI + WebSocket 服务
│   │   ├── models.py            # 数据模型和存储
│   │   └── openclaw_client.py   # OpenClaw WebSocket 客户端
│   └── pyproject.toml
│
├── frontend/                     # TUI 前端
│   ├── src/openclaw_frontend/
│   │   ├── __init__.py
│   │   ├── app.py               # Textual TUI 应用
│   │   └── api_client.py        # 后端 API 客户端
│   └── pyproject.toml
│
├── start-backend.sh              # 启动后端（后台）
├── stop-backend.sh               # 停止后端
├── start-frontend.sh             # 启动 TUI 前端
└── README.md
```

## 🔄 数据流

### 1. 前端启动流程
```
1. 用户运行 ./start-frontend.sh
2. 检查后端是否运行（HTTP 检测）
3. 建立 WebSocket 连接
4. 接收初始化数据（员工列表）
5. 渲染 TUI 界面
```

### 2. 用户发送消息
```
用户输入消息
    ↓
TUI 前端 → HTTP POST /api/employees/{id}/messages
    ↓
后端保存消息 → 发送到 OpenClaw（如果连接）
    ↓
后端通过 WebSocket 广播给所有前端
    ↓
前端收到新消息，更新界面
```

### 3. OpenClaw 状态更新
```
OpenClaw 发送状态更新
    ↓
后端 WebSocket 客户端接收
    ↓
更新内存数据
    ↓
通过 WebSocket 广播给所有前端
    ↓
前端更新员工卡片状态
```

## 🎯 设计优势

| 特性 | 说明 |
|------|------|
| **分离架构** | 后端常驻后台，前端可随时打开/关闭 |
| **持久连接** | 后端保持与 OpenClaw 的 WebSocket 连接 |
| **实时同步** | 多前端可同时连接，数据实时同步 |
| **无状态前端** | TUI 崩溃不影响后端和数据 |
| **服务器友好** | 后端可在服务器长期运行，前端远程连接 |

## 🔌 API 接口

### REST API
- `GET /api/employees` - 获取员工列表
- `GET /api/employees/{id}` - 获取员工详情
- `GET /api/employees/{id}/messages` - 获取消息历史
- `POST /api/employees/{id}/messages` - 发送消息
- `POST /api/employees/{id}/status` - 更新状态

### WebSocket
- `ws://localhost:18765/ws` - 实时数据推送
- 事件类型: `init`, `employee_status_changed`, `new_message`

## 🚀 启动流程

```bash
# 1. 启动后端（后台守护进程）
./start-backend.sh

# 2. 启动 TUI 前端（占用终端，可多次打开）
./start-frontend.sh

# 3. 停止后端
./stop-backend.sh
```
