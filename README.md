# OpenClaw TUI Studio

🎮 **可视化的二进制 OpenClaw 工作室** - 在终端中管理你的 OpenClaw AI 员工团队

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![TUI](https://img.shields.io/badge/TUI-textual-purple.svg)

## 📋 项目概述

OpenClaw TUI Studio 是一个基于终端用户界面（TUI）的可视化管理工具，用于连接和管理 OpenClaw AI 员工。通过直观的界面，你可以：

- 👥 **查看所有员工** - 以可视化卡片形式展示团队中的每一位 OpenClaw 员工
- 💬 **对话下达命令** - 与特定员工进行交互，分配任务和指令
- 📊 **监控工作状态** - 实时查看每位员工的工作状态、进度和输出
- 🔗 **Webhook 集成** - 通过 OpenClaw Webhook API 与员工进行双向通信

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenClaw TUI Studio                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Dashboard  │  │   Chat UI   │  │    Status Monitor   │  │
│  │   (主面板)   │  │  (对话界面)  │  │     (状态监控)       │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         └─────────────────┼────────────────────┘             │
│                           │                                  │
│              ┌────────────▼────────────┐                     │
│              │    TUI Framework        │                     │
│              │      (Textual)          │                     │
│              └────────────┬────────────┘                     │
│                           │                                  │
│              ┌────────────▼────────────┐                     │
│              │    OpenClaw Client      │                     │
│              │    (Webhook Manager)    │                     │
│              └────────────┬────────────┘                     │
└───────────────────────────┼─────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │ OpenClaw API   │
                    │ (Webhook)      │
                    └────────────────┘
```

## 🛠️ 实现方案

### 1. 核心模块设计

### Emoji 图标说明

| Emoji | 含义 | 使用场景 |
|-------|------|----------|
| 🦞 | OpenClaw 员工 | 所有员工卡片、聊天界面 |
| 💬 | 未读消息 | 有未读消息时显示在卡片上 |
| 🟢 | 空闲状态 | 员工处于空闲状态 |
| 🟡 | 工作中状态 | 员工正在处理任务 |
| ⚫ | 离线状态 | 员工当前离线 |
| 📋 | 当前任务 | 显示员工正在执行的任务 |
| 🔄 | 刷新 | 刷新数据按钮 |
| ⚙️ | 设置 | 设置按钮 |
| ❓ | 帮助 | 帮助按钮 |
| 🧑 | 用户 | 聊天界面中的用户头像 |

### 键盘导航指南

完全支持键盘操作，无需鼠标：

| 按键 | 功能 |
|------|------|
| ↑ / ↓ / ← / → | 在员工卡片间导航移动 |
| Tab | 在工具栏按钮和员工卡片间切换焦点 |
| Enter | 进入对话 / 发送消息 / 点击按钮 |
| Space | 查看员工详情 |
| Home | 跳到第一个员工 |
| End | 跳到最后一个员工 |
| Esc | 从对话返回工作室 |
| q | 退出应用 |
| r | 刷新数据 |
| ? | 显示帮助 |

#### 1.1 TUI 界面层 (`ui/`)

```
ui/
├── __init__.py
├── app.py                 # Textual App 主入口
├── screens/
│   ├── __init__.py
│   ├── dashboard.py       # 主面板 - 员工总览
│   ├── chat.py            # 聊天界面 - 与员工对话
│   └── settings.py        # 设置界面 - 配置管理
├── widgets/
│   ├── __init__.py
│   ├── employee_card.py   # 员工卡片组件
│   ├── employee_list.py   # 员工列表组件
│   ├── chat_panel.py      # 聊天面板组件
│   ├── status_bar.py      # 状态栏组件
│   └── log_viewer.py      # 日志查看器
└── styles/
    ├── __init__.py
    └── styles.css         # Textual CSS 样式
```

#### 1.2 OpenClaw 集成层 (`openclaw/`)

```
openclaw/
├── __init__.py
├── client.py              # Webhook 客户端
├── webhook_server.py      # 本地 Webhook 接收服务
├── models.py              # 数据模型 (Employee, Task, Message)
├── events.py              # 事件定义
└── exceptions.py          # 异常定义
```

#### 1.3 业务逻辑层 (`core/`)

```
core/
├── __init__.py
├── employee_manager.py    # 员工管理器
├── session_manager.py     # 会话管理器
├── task_manager.py        # 任务管理器
└── state_manager.py       # 状态管理器 ( reactive state )
```

### 2. 关键功能实现

#### 2.1 员工卡片展示

每个员工以卡片形式展示，包含：
- **头像/标识** - 使用 ASCII Art 或 Unicode 字符
- **姓名** - 员工名称
- **角色** - 职责描述
- **状态指示器** - 🟢 空闲 / 🟡 工作中 / 🔴 离线
- **当前任务** - 简短的任务描述
- **快捷操作** - 点击展开详情/开始对话

#### 2.2 对话系统

```
┌────────────────────────────────────────────────────────────────┐
│← 返回  🦞 与 Alice 对话 (代码审查专家)                          │
├────────────────────────────────────────────────────────────────┤
│  🦞 Alice · 10:32                                              │
│  收到！我已经开始分析代码库，预计需要 5 分钟完成。              │
│                                                                │
│  🧑 你 · 10:30                                                 │
│  请帮我分析这个项目的代码质量                                   │
│                                                                │
│  🦞 正在输入...                                                │
├────────────────────────────────────────────────────────────────┤
│ 💭 输入消息或命令...                                           │
└────────────────────────────────────────────────────────────────┘
```

支持特性：
- `@mention` 快速选择员工
- 命令历史 (上下箭头)
- 实时状态反馈
- Markdown 渲染支持

#### 2.3 状态监控

实时显示：
- 员工在线状态
- 当前执行的任务
- 任务进度条
- 最近输出日志
- CPU/内存使用（如果 OpenClaw API 提供）

### 3. Webhook 集成方案

#### 3.1 双向通信架构

```
┌─────────────────┐         Webhook          ┌─────────────────┐
│   TUI Studio    │  <------------------>   │  OpenClaw API   │
│                 │    (任务下发/状态回传)    │                 │
│  ┌───────────┐  │                        │  ┌───────────┐  │
│  │  Outgoing │──┤── POST /webhook/send   │  │  Agent    │  │
│  │  Webhook  │  │                        │  │  System   │  │
│  └───────────┘  │                        │  └───────────┘  │
│                 │                        │                 │
│  ┌───────────┐  │  POST /local-webhook   │  ┌───────────┐  │
│  │  Incoming │◄─┤◄----------------------─┤──│  Events   │  │
│  │  Webhook  │  │   (status/progress)    │  │  Emitter  │  │
│  └───────────┘  │                        │  └───────────┘  │
└─────────────────┘                        └─────────────────┘
```

#### 3.2 Webhook 事件类型

**Outgoing Events (TUI → OpenClaw):**
- `task.assign` - 分配任务
- `task.cancel` - 取消任务
- `message.send` - 发送消息
- `employee.query` - 查询员工状态

**Incoming Events (OpenClaw → TUI):**
- `status.update` - 状态更新
- `progress.report` - 进度报告
- `message.receive` - 接收消息
- `task.complete` - 任务完成
- `error.report` - 错误报告

#### 3.3 配置格式

```yaml
# config.yaml
openclaw:
  api_base: "https://api.openclaw.ai"
  api_key: "${OPENCLAW_API_KEY}"
  webhook:
    # 发送消息到 OpenClaw
    send_url: "${OPENCLAW_WEBHOOK_SEND_URL}"
    # 接收 OpenClaw 回调
    receive_port: 8765
    receive_path: "/webhook"
    secret: "${WEBHOOK_SECRET}"

employees:
  - id: "alice-001"
    name: "Alice"
    role: "代码审查专家"
    avatar: "👩‍💻"
  - id: "bob-002"
    name: "Bob"
    role: "文档生成助手"
    avatar: "👨‍💻"
  - id: "carol-003"
    name: "Carol"
    role: "测试工程师"
    avatar: "🧪"

ui:
  theme: "dark"
  refresh_interval: 2  # 秒
  max_log_lines: 1000
```

### 4. 项目文件结构

```
openclaw-tui-studio/
├── .gitignore
├── README.md
├── LICENSE
├── requirements.txt           # Python 依赖
├── pyproject.toml            # 项目配置
├── config.yaml.example       # 配置示例
├── src/
│   └── openclaw_tui/
│       ├── __init__.py
│       ├── __main__.py       # python -m 入口
│       ├── app.py            # TUI 主应用
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── screens/
│       │   ├── widgets/
│       │   └── styles/
│       ├── openclaw/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── webhook_server.py
│       │   ├── models.py
│       │   └── events.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── employee_manager.py
│       │   ├── session_manager.py
│       │   └── state_manager.py
│       └── utils/
│           ├── __init__.py
│           ├── config.py
│           └── logger.py
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   └── test_widgets.py
└── docs/
    ├── architecture.md
    └── api.md
```

### 5. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| TUI Framework | [Textual](https://textual.textualize.io/) | Python 原生、组件丰富、CSS 样式支持、活跃的社区 |
| HTTP Client | `httpx` | 异步支持、类型提示、现代 API |
| Webhook Server | `fastapi` + `uvicorn` | 高性能、异步、自动文档生成 |
| 数据验证 | `pydantic` | 类型安全、序列化、配置管理 |
| 状态管理 | `reactive` (Textual内置) | 响应式更新、与 TUI 无缝集成 |
| 配置管理 | `pydantic-settings` | 环境变量支持、类型验证 |

### 6. 核心交互流程

#### 6.1 启动流程

```
1. 加载配置文件
2. 初始化 StateManager (reactive state)
3. 启动 Webhook 接收服务器 (后台线程)
4. 连接 OpenClaw API，获取员工列表
5. 启动 TUI App
6. 开始定期轮询状态 (fallback)
```

#### 6.2 发送命令流程

```
用户输入命令
    ↓
解析 @mention 识别目标员工
    ↓
SessionManager 创建/恢复会话
    ↓
OpenClawClient 发送 Webhook 请求
    ↓
更新 UI 状态为"发送中"
    ↓
等待 Webhook 回调 或 超时
    ↓
更新消息状态和员工状态
    ↓
UI 自动刷新显示
```

#### 6.3 接收状态更新流程

```
OpenClaw 发送 Webhook 回调
    ↓
WebhookServer 接收并验证签名
    ↓
解析事件类型和 payload
    ↓
发布到内部 EventBus
    ↓
StateManager 更新对应员工状态
    ↓
Textual reactive 自动触发 UI 更新
    ↓
特定 Widget 重新渲染
```

### 7. 界面布局设计

#### 7.1 主界面 (Dashboard)

```
┌────────────────────────────────────────────────────────────────┐
│ OpenClaw TUI Studio                                    10:32   │
├────────────────────────────────────────────────────────────────┤
│ 🔄 刷新 │ ⚙️ 设置 │ ❓ 帮助                                     │
├────────────────────────────────────────────────────────────────┤
│ 🦞 OpenClaw 工作室 - 员工列表                                 │
│                                                                │
│ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐      │
│ │ 🟢 空闲  💬    │ │ 🟡 工作中 💬💬 │ │ 🟢 空闲        │      │
│ │     🦞        │ │     🦞        │ │     🦞        │      │
│ │    Alice      │ │     Bob       │ │    Carol      │      │
│ │  代码审查专家  │ │  文档生成助手  │ │  测试工程师    │      │
│ │ 📋 无任务      │ │ 📋 生成API... │ │ 📋 无任务      │      │
│ └────────────────┘ └────────────────┘ └────────────────┘      │
│                                                                │
│ ┌────────────────┐ ┌────────────────┐                         │
│ │ ⚫ 离线        │ │ 🟡 工作中 💬   │ │                         │
│ │     🦞        │ │     🦞        │ │                         │
│ │     Dave      │ │     Eve       │ │                         │
│ │  DevOps 专家   │ │  数据分析助手  │ │                         │
│ │ 📋 无任务      │ │ 📋 分析日志...│ │                         │
│ └────────────────┘ └────────────────┘                         │
│                                                                │
│ ↑/↓/←/→ 导航 │ Enter 对话 │ Space 详情 │ q 退出               │
├────────────────────────────────────────────────────────────────┤
│ 🟢 已连接  │  🦞 4/5  │  📋 2  │  💬 3                           │
└────────────────────────────────────────────────────────────────┘
```
*注：选中卡片会有高亮边框，使用方向键导航，Enter 进入对话*

#### 7.2 对话界面 (Chat)

```
┌────────────────────────────────────────────────────────────────┐
│← 返回  🦞 与 Alice 对话 (代码审查专家)                          │
├────────────────────────────────────────────────────────────────┤
│ 🦞 Alice · 刚刚                                                │
│ 已完成代码分析，发现 3 个潜在问题和 2 个优化建议：              │
│                                                                │
│ 1. ⚠️ 第 42 行存在未使用的导入                                  │
│ 2. ⚠️ 函数 `process_data` 缺少类型注解                          │
│ 3. 💡 建议使用列表推导式优化循环                                │
│                                                                │
│ 需要我生成修复后的代码吗？                                      │
│                                                                │
│ 🧑 你 · 10:30                                                  │
│ @alice 请帮我 review src/core/app.py 这个文件                  │
│                                                                │
│ 🦞 正在输入...                                                 │
├────────────────────────────────────────────────────────────────┤
│ 💭 输入消息或命令...                                           │
├────────────────────────────────────────────────────────────────┤
│ Tab 切换 │ Enter 发送 │ Esc 返回工作室                            │
└────────────────────────────────────────────────────────────────┘
```

### 8. 扩展性设计

#### 8.1 插件系统 (未来)

```python
# plugins/base.py
class Plugin(ABC):
    @abstractmethod
    def on_employee_status_change(self, employee: Employee, old_status: Status):
        pass
    
    @abstractmethod
    def on_message_received(self, message: Message):
        pass
```

#### 8.2 自定义主题

支持通过 CSS 文件自定义界面外观：

```css
/* themes/custom.css */
EmployeeCard {
    border: solid $primary;
    background: $surface-darken-1;
}

EmployeeCard:hover {
    background: $surface-darken-2;
}

StatusIndicator.active {
    color: $success;
}
```

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/openclaw-tui-studio.git
cd openclaw-tui-studio

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置

```bash
# 复制配置模板
cp config.yaml.example config.yaml

# 编辑配置，填入你的 OpenClaw API 密钥
vim config.yaml
```

### 运行

```bash
# 方式1: 作为模块运行
python -m openclaw_tui

# 方式2: 使用入口脚本
python src/openclaw_tui/app.py
```

### 基本操作

1. **启动后**，使用 ↑/↓/←/→ 方向键选择员工
2. **选中员工**（卡片会有高亮边框）后按 Enter 进入对话
3. **在对话界面**输入消息，按 Enter 发送
4. **按 Esc** 返回工作室主界面
5. **按 q** 退出应用

## 📦 依赖列表

```
textual>=0.45.0
httpx>=0.25.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
pyyaml>=6.0.1
rich>=13.7.0
watchdog>=3.0.0
```

## 🎯 开发路线图

### Phase 1: 基础框架 (MVP)
- [ ] 项目结构搭建
- [ ] Textual TUI 基础框架
- [ ] 基础布局 (Dashboard + Chat)
- [ ] EmployeeCard 组件
- [ ] OpenClaw Client 基础实现

### Phase 2: Webhook 集成
- [ ] Webhook 接收服务器
- [ ] 消息发送/接收
- [ ] 状态同步机制
- [ ] 配置管理系统

### Phase 3: 功能完善
- [ ] 命令历史
- [ ] 文件附件支持
- [ ] 搜索/过滤员工
- [ ] 任务队列管理

### Phase 4: 高级特性
- [ ] 插件系统
- [ ] 自定义主题
- [ ] 日志导出
- [ ] 快捷键自定义

## 📝 License

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

*Made with ❤️ for OpenClaw*
