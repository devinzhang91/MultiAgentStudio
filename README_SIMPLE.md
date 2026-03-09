# 🦞 OpenClaw TUI Studio - 简洁版

单文件 TUI 应用，无需前后端分离，直接运行即可使用。

## ✨ 特点

- **单文件**: 只有一个 `openclaw_studio.py`，无需复杂架构
- **本地存储**: 员工配置保存在 `~/.openclaw_studio/employees.json`
- **多平台**: Python + Textual，支持 macOS/Linux/Windows
- **独立连接**: 每个员工有独立的 OpenClaw WebSocket 连接

## 🚀 快速开始

### 安装依赖

```bash
pip3 install textual aiohttp cryptography
```

### 运行

```bash
# 方式1: 直接运行
python3 openclaw_studio.py

# 方式2: 使用脚本
./run.sh
```

## 📁 文件结构

```
openclaw-tui-studio/
├── openclaw_studio.py    # 主程序（单文件）
├── run.sh                # 启动脚本
└── ~/.openclaw_studio/   # 数据目录
    ├── employees.json    # 员工配置
    └── identity_*.json   # 员工身份文件
```

## ⚙️ 配置员工

首次运行会自动创建示例配置。编辑 `~/.openclaw_studio/employees.json`：

```json
{
  "emp-001": {
    "id": "emp-001",
    "name": "Alice",
    "role": "代码审查专家",
    "status": "offline",
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

## ⌨️ 快捷键

| 按键 | 功能 |
|------|------|
| `Enter` | 进入对话 |
| `Space` | 查看员工详情 |
| `a` | 添加员工（开发中） |
| `r` | 刷新 |
| `q` | 退出 |
| `Esc` | 返回 |

## 🦞 什么是 OpenClaw?

OpenClaw 是一个 AI Agent 网关协议，通过 WebSocket 连接 AI 员工（Agent）。

每个员工需要配置：
- `base_url`: OpenClaw Gateway 地址
- `token`: 认证令牌
- `session_key`: 会话标识

## 📝 TODO

- [ ] 添加员工界面（GUI）
- [ ] 消息历史保存
- [ ] 多行消息支持
- [ ] 更好的错误提示

## 📄 License

MIT
