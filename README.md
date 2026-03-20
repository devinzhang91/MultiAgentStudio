# 🦞 MushTech Studio - MultiAgentStudio

基于 OpenClaw 的多智能体团队 TUI 管理工具。

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ 功能特性

- **多智能体管理**：创建、删除、编辑智能体，实时监控状态
- **智能聊天**：独立会话上下文，消息持久化，思考状态提示
- **模板系统**：内置软件工程、Remotion 视频、股票分析、Slidev PPT 等团队模板
- **纯键盘操作**：Vim 风格快捷键，无需鼠标

---

## 📸 界面预览

### 主界面 - 智能体监控

主界面展示所有智能体的实时状态，包括在线状态、角色信息和最新消息预览。

<img src="images/AgentsWorkModel.png" width="800" alt="智能体监控界面">

### 聊天界面

与智能体进行对话，支持 Markdown 渲染、思考状态提示和流式输出。

<img src="images/UI_CHAT.png" width="800" alt="聊天界面">

### 用户交互模式

支持多种交互模式，包括命令行、配置界面和 TUI 界面。

<img src="images/UserInteraction.png" width="800" alt="用户交互模式">

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
| `F5` | 立即同步消息 |
| `Ctrl+C` | 退出程序 |

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

MushTech Studio 提供四种预配置的专业团队模板，每个模板都包含完整的角色分工和协作流程。

### 1️⃣ 软件工程团队

完整的软件开发团队，支持从需求分析到交付的全流程开发。

| 角色 | 英文名 | 职责 |
|------|--------|------|
| 🎯 **项目经理** | Alex | 主脑，负责需求分析、任务分配、进度跟踪和跨团队协调 |
| 🎨 **UI/UX 设计师** | Luna | 界面设计、用户体验优化、原型制作和设计系统维护 |
| 💻 **软件开发工程师** | Kai | 前后端开发、API设计、架构实现和性能优化 |
| 📝 **技术文档工程师** | Iris | 技术文档编写、API文档、用户手册和知识库维护 |
| 🔍 **综合观察员** | Zoe | 技能搜索与审查、网络信息检索、任务进度监控 |

**适用场景**：软件开发项目、产品设计、技术架构设计

---

### 2️⃣ Remotion 视频工作室

专业的视频创作团队，专注于代码视频和创意视频内容制作。

| 角色 | 英文名 | 职责 |
|------|--------|------|
| 🎬 **视频导演** | Chris | 主脑，负责视频创意策划、导演分镜、叙事结构和团队协调 |
| ✍️ **视频编剧** | Aaron | 视频脚本撰写、旁白文案、故事结构设计和内容策略 |
| 💻 **Remotion核心开发** | James | Remotion核心开发、React动画、CLI扩展和架构设计 |
| 🎵 **媒体特效工程师** | Hans | 音效集成、视觉特效、媒体处理和渲染优化 |
| 🔍 **视频质量分析师** | Roger | 视频质量分析、测试验证、问题诊断和代码审查 |

**适用场景**：代码教程视频、技术演示视频、产品宣传片制作

---

### 3️⃣ 股票分析团队

专业投资研究团队，采用去中心化协作模式，提供全面的投资决策支持。

| 角色 | 英文名 | 职责 |
|------|--------|------|
| 📊 **首席分析师** | Warren | 主脑，价值投资专家，负责投资组合管理和长期策略制定 |
| 🏛️ **宏观研究员** | Ray | 宏观经济分析、货币政策研究、经济周期判断 |
| 🏭 **行业研究员** | Peter | 行业分析、竞争格局研究、商业模式评估 |
| 📡 **实时数据收集员** | Paul | A股/美股API数据获取、实时行情采集、多周期数据收集 |
| 🔍 **综合观察员** | Nassim | 技能搜索与审查、网络信息检索、任务进度监控 |

**适用场景**：价值投资分析、行业研究、市场趋势判断、投资组合管理

---

### 4️⃣ Slidev PPT 设计工作室

专业的幻灯片设计与制作团队，使用 Slidev 技术打造精美、交互丰富的演示文稿。

| 角色 | 英文名 | 职责 |
|------|--------|------|
| 🎯 **PPT项目总监** | Steven | 主脑，负责需求分析、内容规划、项目排期和质量把控 |
| ✍️ **PPT内容架构师** | Elena | 内容策略、信息架构、布局设计和 Slidev 语法 |
| 🎨 **PPT视觉设计师** | Aria | 视觉设计、主题定制、样式开发、动画设计 |
| 💻 **PPT代码展示专家** | Linus | 代码展示、Magic Move动画、代码高亮、Monaco编辑器 |
| 🚀 **PPT集成工程师** | DevOps | 导出部署、Mermaid图表、PlantUML、PDF生成 |
| 🖼️ **绘图大师** | Pixel | AI图像生成、提示词工程、视觉创意、风格把控 |

**适用场景**：技术演讲幻灯片、产品发布会 PPT、学术报告、培训课件制作

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
│       ├── prompts/       # 角色配置 JSON
│       └── *.py           # 模板实现
├── data/                  # 数据存储
├── logs/                  # 运行日志
├── images/                # 截图和文档图片
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
