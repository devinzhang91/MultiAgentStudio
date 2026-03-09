# OpenClaw TUI Studio 架构文档

## 概述

本文档详细描述 OpenClaw TUI Studio 的技术架构和设计决策。

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Dashboard  │  │  Chat Screen │  │ Settings Screen  │  │
│  │    Screen    │  │              │  │                  │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         └──────────────────┼───────────────────┘            │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                      UI Components Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ Employee │  │ Employee │  │  Chat    │  │   Status    │  │
│  │  Card    │  │   List   │  │  Panel   │  │    Bar      │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                      State Management                        │
│                    (Textual Reactive)                        │
│                                                              │
│   reactive_var ──> Widget.update() ──> UI Refresh            │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                      Core Business Logic                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Employee   │  │   Session    │  │  Task Manager    │  │
│  │   Manager    │  │   Manager    │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                     OpenClaw Integration                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Webhook    │  │   Webhook    │  │  Data Models     │  │
│  │    Client    │  │   Server     │  │  (Pydantic)      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────┘  │
│         └──────────────────┼───────────────────┘            │
└────────────────────────────┼────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   OpenClaw API  │
                    │    (Webhook)    │
                    └─────────────────┘
```

## 模块职责

### 1. UI Layer (`ui/`)

- **Screens**: 完整页面，管理布局和导航
- **Widgets**: 可复用的 UI 组件
- **Styles**: CSS 样式定义

### 2. Core Layer (`core/`)

- **EmployeeManager**: 员工数据的 CRUD 和状态管理
- **SessionManager**: 用户会话和对话历史
- **TaskManager**: 任务分配和追踪
- **StateManager**: 全局响应式状态

### 3. OpenClaw Layer (`openclaw/`)

- **Client**: 发送 Webhook 请求到 OpenClaw
- **WebhookServer**: 接收 OpenClaw 的事件推送
- **Models**: Pydantic 数据模型
- **Events**: 内部事件定义

## 数据流

### 状态更新流

```
1. OpenClaw Webhook -> WebhookServer
2. WebhookServer validates & parses event
3. Event published to EventBus
4. EmployeeManager/StateManager updates reactive state
5. Textual detects state change
6. Affected Widgets re-render automatically
```

### 用户命令流

```
1. User types command in ChatPanel
2. SessionManager creates/retrieves session
3. Command parsed for @mentions
4. OpenClawClient sends Webhook request
5. UI shows "sending" indicator
6. Wait for response (async)
7. Update message status on response
8. (Optional) Receive status via incoming webhook
```

## 关键技术决策

### 为什么选择 Textual?

1. **Python 原生**: 与 OpenClaw Python SDK 无缝集成
2. **组件化**: 类似现代 Web 框架的组件系统
3. **响应式**: 内置 reactive state 管理
4. **CSS 样式**: 支持类似 CSS 的样式定义
5. **活跃社区**: 持续更新和丰富的文档

### Webhook 双向通信

- **Outgoing**: 使用 `httpx` 发送异步请求
- **Incoming**: 使用 `FastAPI` + `uvicorn` 运行轻量级服务器
- **优势**: 实时状态更新，减少轮询开销

### 状态管理策略

- 使用 Textual 的 `reactive` 进行细粒度状态绑定
- 避免全局状态污染，按模块划分 StateManager
- 事件总线解耦各模块

## 扩展点

1. **插件系统**: 基于 EventBus 的订阅模式
2. **自定义主题**: CSS 文件热加载
3. **多后端支持**: 抽象 Client 接口，支持其他 AI 平台
