# 🦞 MultiAgentStudio

基于 OpenClaw 的多智能体团队 TUI 管理工具。

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ 功能特性

- **多智能体管理**：创建、删除、编辑智能体，实时监控状态
- **智能聊天**：独立会话上下文，消息持久化，思考状态提示
- **模板系统**：内置软件工程、Remotion 视频、股票分析等团队模板
- **纯键盘操作**：Vim 风格快捷键，无需鼠标

---

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/devinzhang91/MultiAgentStudio.git
cd MultiAgentStudio

# 运行启动脚本
./run.sh
```

### CLI 命令

```bash
# 启动主界面（默认）
python3 -m mushtech_studio

# 启动配置界面
python3 -m mushtech_studio config

# 重置配置
python3 -m mushtech_studio reset

# 强制重置（跳过确认）
python3 -m mushtech_studio reset --force
```

---

## ⌨️ 快捷键

### 主界面
| 按键 | 功能 |
|------|------|
| `↑↓←→` | 导航选择 |
| `Enter` | 打开聊天 |
| `m` | 管理智能体 |
| `r` | 刷新列表 |
| `q` | 退出 |
| `?` | 显示帮助 |

### 聊天界面
| 按键 | 功能 |
|------|------|
| `Enter` | 发送消息 |
| `Tab` | 切换焦点 |
| `ESC` | 返回主界面 |

---

## ⚙️ 配置

配置文件位置：`data/studio_config.json`

```json
{
  "gateway_url": "http://127.0.0.1:18789",
  "gateway_token": "your-token-here",
  "architecture": "hybrid",
  "studio_type": "software_engineering",
  "base_workspace": "/path/to/workspace"
}
```

配置项说明：
- **gateway_url**: OpenClaw Gateway 地址
- **gateway_token**: Gateway 鉴权令牌
- **architecture**: 架构模式（centralized/decentralized/hybrid）
- **studio_type**: 团队模板类型
- **base_workspace**: 工作区根目录

---

## 🎨 模板系统

### 软件工程团队
- **mush-pm**: 产品经理（主脑）
- **mush-ui**: UI 设计师
- **mush-dev**: 程序员
- **mush-qa**: 测试工程师
- **mush-doc**: 文档工程师

### Remotion 视频工作室
- **video-director**: 视频导演（主脑）
- **script-writer**: 脚本编剧
- **visual-designer**: 视觉设计师
- **remotion-dev**: Remotion 开发
- **video-editor**: 后期剪辑

### 股票分析团队
- **lead-analyst**: 首席分析师（主脑）
- **macro-researcher**: 宏观研究员
- **sector-researcher**: 行业研究员
- **technical-analyst**: 技术分析师
- **risk-assessor**: 风险评估师

---

## 🏗️ 项目结构

```
openclaw-tui-studio/
├── mushtech_studio/       # 主程序包
│   ├── app.py             # 主应用
│   ├── cli.py             # 命令行接口
│   ├── client.py          # WebSocket 客户端
│   ├── models.py          # 数据模型
│   ├── message_manager.py # 消息管理
│   └── templates/         # 团队模板
├── data/                  # 数据存储
├── logs/                  # 运行日志
└── run.sh                 # 启动脚本
```

---

## 📋 必要条件

- **Python**: 3.8+
- **OpenClaw CLI**: 已安装并配置
- **OpenClaw Gateway**: 运行中

---

## 🔧 开发

```bash
# 语法检查
python3 -m py_compile mushtech_studio/*.py

# 查看日志
tail -f logs/mushtech_*.log
```

---

## 📄 许可证

[MIT](LICENSE)
