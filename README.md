# 🦞 OpenClaw TUI Studio

可视化的 OpenClaw 员工管理工具 - 单文件 TUI 应用。

## ✨ 特点

- **单文件**: 只有一个 `openclaw_studio.py`，无需复杂架构
- **直接运行**: 无需前后端分离，一条命令启动
- **本地存储**: 员工配置保存在项目目录的 `data/employees.json`
- **多平台**: Python + Textual，支持 macOS/Linux/Windows
- **独立连接**: 每个员工有独立的 OpenClaw WebSocket 连接

## 🚀 快速开始

### 方式1: 使用脚本（推荐）

脚本会自动创建虚拟环境并安装依赖：

```bash
./run.sh
```

### 方式2: 手动运行

如果你不想用虚拟环境：

```bash
# 安装依赖
pip3 install textual aiohttp cryptography

# 运行
python3 openclaw_studio.py
```

## 📁 项目结构

```
openclaw-tui-studio/
├── openclaw_studio.py    # 主程序（单文件，~800行）
├── run.sh                # 启动脚本
├── README.md             # 本文件
├── LICENSE               # MIT 许可证
├── .gitignore            # Git 忽略配置
└── data/                 # 数据目录（自动创建）
    ├── employees.json    # 员工信息配置文件
    └── identities/       # 员工身份文件（自动创建）
        ├── emp-001.json
        └── emp-002.json
```

## ⚙️ 配置员工

编辑 `data/employees.json` 文件来添加/修改员工：

```json
{
  "emp-001": {
    "id": "emp-001",
    "name": "Alice",
    "role": "代码审查专家",
    "status": "offline",
    "current_task": "",
    "unread_count": 0,
    "last_error": "",
    "config": {
      "base_url": "wss://your-openclaw-gateway.com",
      "token": "your_token_here",
      "session_key": "alice",
      "timeout": 120,
      "enabled": true
    }
  }
}
```

### 配置项说明

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `base_url` | OpenClaw Gateway 地址 | `wss://gateway.openclaw.com` |
| `token` | 认证令牌 | `oc_token_xxx` |
| `session_key` | 会话标识 | `alice` |
| `timeout` | 请求超时（秒） | `120` |
| `enabled` | 是否启用连接 | `true`/`false` |

### 添加新员工

1. 复制一个现有员工配置块
2. 修改 `id`（如 `emp-003`）
3. 修改 `name`、`role` 等信息
4. 配置 `config` 中的连接参数
5. 保存文件并重启程序

## ⌨️ 快捷键

### 主界面

| 按键 | 功能 |
|------|------|
| `↑/↓/←/→` | 导航员工卡片 |
| `Enter` | 进入对话 |
| `Space` | 查看员工详情 |
| `a` | 添加员工（开发中） |
| `r` | 刷新列表 |
| `q` | 退出应用 |

### 对话界面

| 按键 | 功能 |
|------|------|
| `Enter` | 发送消息 |
| `Esc` | 返回主界面 |

## 🦞 什么是 OpenClaw?

OpenClaw 是一个 AI Agent 网关协议，通过 WebSocket 连接 AI 员工（Agent）。

每个员工可以独立配置连接参数，支持同时管理多个 OpenClaw 员工。

## 📦 依赖

- Python 3.9+
- textual >= 0.45.0
- aiohttp >= 3.9.0
- cryptography >= 41.0.0

## 📝 TODO

- [x] 员工列表展示
- [x] OpenClaw WebSocket 连接
- [x] 消息发送/接收
- [x] 员工详情查看
- [ ] 添加员工 GUI 界面
- [ ] 消息历史保存
- [ ] 员工状态实时更新
- [ ] 更好的错误提示

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

*Made with ❤️ for OpenClaw*
