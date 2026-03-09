# 🦞 OpenClaw TUI Studio

可视化的 OpenClaw 员工管理工作室 - 交互式终端界面。

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![TUI](https://img.shields.io/badge/TUI-Textual-purple.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ 特点

- **🎨 精美界面**: Emoji 图标 + 平面设计，视觉体验佳
- **🖱️ 鼠标支持**: 点击选择、双击进入对话
- **⌨️ 键盘导航**: 方向键导航，Enter/Space 交互
- **📁 本地存储**: 员工信息保存在项目目录
- **🔧 简单易用**: 单文件运行，无需复杂配置

## 🚀 快速开始

```bash
# 克隆项目
git clone https://github.com/yourusername/openclaw-tui-studio.git
cd openclaw-tui-studio

# 一键启动（自动创建虚拟环境+安装依赖）
./run.sh
```

## 🎮 操作指南

### 🖱️ 鼠标操作

| 操作 | 功能 |
|------|------|
| 点击员工卡片 | 选中员工 |
| 双击员工卡片 | 进入对话 |
| 点击按钮 | 执行操作 |

### ⌨️ 键盘操作

| 按键 | 功能 |
|------|------|
| `↑` `↓` `←` `→` | 导航选择员工 |
| `Enter` | 进入对话 |
| `Space` | 打开员工菜单 |
| `a` | 添加新员工 |
| `r` | 刷新列表 |
| `q` | 退出应用 |
| `Esc` | 返回/关闭 |

### 📊 Emoji 图标说明

| 图标 | 含义 |
|------|------|
| 🦞 | OpenClaw 员工 |
| 💬 | 未读消息 |
| 🟢 | 空闲状态 |
| 🟡 | 工作中 |
| ⚫ | 离线状态 |
| 📋 | 当前任务 |

## 📁 项目结构

```
openclaw-tui-studio/
├── openclaw_studio.py    # 主程序（单文件）
├── run.sh                # 启动脚本
├── README.md             # 本文件
├── LICENSE               # MIT 许可证
└── data/                 # 数据目录
    ├── employees.json    # 员工配置文件
    └── identities/       # 身份文件（自动创建）
```

## ⚙️ 配置员工

编辑 `data/employees.json`：

```json
{
  "emp-001": {
    "id": "emp-001",
    "name": "Alice",
    "role": "代码审查专家",
    "status": "offline",
    "avatar": "🦞",
    "unread_count": 0,
    "current_task": "",
    "enabled": true,
    "config": {
      "base_url": "wss://your-gateway.com",
      "token": "your_token",
      "session": "alice"
    }
  }
}
```

### 添加新员工

1. 按 `a` 键打开添加界面
2. 填写名称、角色等信息
3. 保存后自动显示在工作室

## 💬 对话功能

1. 选中员工，按 `Enter` 或双击进入对话
2. 输入消息，按 `Enter` 发送
3. 按 `Esc` 返回工作室

## 📦 依赖

- Python 3.9+
- textual >= 0.45.0
- aiohttp >= 3.9.0
- cryptography >= 41.0.0

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

*Made with ❤️ for OpenClaw*
