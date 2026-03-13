#!/usr/bin/env python3
"""
MushTech 多智能体团队初始化脚本 - 完整版

创建完整的代码外包团队：
- Alex Chen (Product Manager) - 主脑
- Luna Vega (UI Designer) - 专才  
- Kai Nakamura (Programmer) - 专才
- Zoe Mitchell (Code Tester) - 专才
- Iris Park (Document Writer) - 专才

功能：
1. 创建工作区和 SOUL.md 人格定义
2. 通过 CLI 创建 agents
3. 配置 agentToAgent 和 subagents 权限
4. 配置 tools（sessions.visibility 等）
5. 配置 bindings
6. 重启 Gateway
7. 创建初始 sessions

使用架构：混合模式（生产级推荐）
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


# MushTech 团队配置 - 每个角色都有独特的名字、emoji和性格
MUSHTECH_TEAM = [
    {
        "id": "mush-pm",
        "name": "Alex Chen",
        "display_name": "Alex",
        "role": "项目经理 | 主脑调度",
        "type": "main_brain",
        "avatar": "🎯",
        "emoji": "🎯",
        "workspace": "/Users/zhangyoujin/MushTech-openclaw/workspace/pm-alex",
        "model": "volcengine/glm-4.7",
        "description": "经验丰富的技术项目经理，擅长分析复杂需求和协调团队，决策果断且善于沟通",
        "personality": "经验丰富的技术项目经理，擅长分析复杂需求和协调团队，决策果断且善于沟通",
        "specialty": "需求分析、任务分配、进度跟踪、质量把控、跨团队协调",
        "is_default": True,
    },
    {
        "id": "mush-ui",
        "name": "Luna Vega",
        "display_name": "Luna",
        "role": "UI/UX 设计师",
        "type": "specialist",
        "avatar": "🎨",
        "emoji": "🎨",
        "workspace": "/Users/zhangyoujin/MushTech-openclaw/workspace/ui-luna",
        "model": "volcengine/glm-4.7",
        "description": "充满创意的设计师，追求界面的美学与用户体验完美平衡，对色彩和排版有敏锐直觉",
        "personality": "充满创意的设计师，追求界面的美学与用户体验完美平衡，对色彩和排版有敏锐直觉",
        "specialty": "界面设计、用户体验优化、原型制作、视觉设计、交互设计",
    },
    {
        "id": "mush-dev",
        "name": "Kai Nakamura",
        "display_name": "Kai",
        "role": "开发工程师",
        "type": "specialist",
        "avatar": "💻",
        "emoji": "💻",
        "workspace": "/Users/zhangyoujin/MushTech-openclaw/workspace/dev-kai",
        "model": "volcengine/glm-4.7",
        "description": "极客精神的全栈工程师，代码严谨且注重性能优化，喜欢钻研新技术和解决技术难题",
        "personality": "极客精神的全栈工程师，代码严谨且注重性能优化，喜欢钻研新技术和解决技术难题",
        "specialty": "后端开发、API设计、数据库设计、架构实现、性能优化",
    },
    {
        "id": "mush-qa",
        "name": "Zoe Mitchell",
        "display_name": "Zoe",
        "role": "测试工程师",
        "type": "specialist",
        "avatar": "🧪",
        "emoji": "🧪",
        "workspace": "/Users/zhangyoujin/MushTech-openclaw/workspace/qa-zoe",
        "model": "volcengine/glm-4.7",
        "description": "严谨细致的质量保障专家，善于发现边界情况和潜在问题，对产品质量有极高要求",
        "personality": "严谨细致的质量保障专家，善于发现边界情况和潜在问题，对产品质量有极高要求",
        "specialty": "测试用例编写、自动化测试、Bug追踪、性能测试、安全测试",
    },
    {
        "id": "mush-doc",
        "name": "Iris Park",
        "display_name": "Iris",
        "role": "技术文档编写",
        "type": "specialist",
        "avatar": "📝",
        "emoji": "📝",
        "workspace": "/Users/zhangyoujin/MushTech-openclaw/workspace/doc-iris",
        "model": "volcengine/glm-4.7",
        "description": "文字工匠型的文档专家，擅长将复杂技术概念转化为通俗易懂的文档，注重逻辑性和可读性",
        "personality": "文字工匠型的文档专家，擅长将复杂技术概念转化为通俗易懂的文档，注重逻辑性和可读性",
        "specialty": "技术文档编写、用户手册、API文档、会议纪要、知识库维护",
    },
]

# 工作区基础路径
BASE_WORKSPACE = "/Users/zhangyoujin/MushTech-openclaw/workspace"

# OpenClaw 配置文件路径
OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"


def print_banner():
    """打印欢迎信息"""
    banner = """
    🐠 MushTech Multi-Agent Team Setup 🐠
    
    正在初始化代码外包团队...
    
    团队成员:
      🧔 Alex Chen      - 项目经理/主脑
      🌙 Luna Vega      - UI/UX设计师
      ⚙️  Kai Nakamura   - 开发工程师
      🧪 Zoe Mitchell   - 测试工程师
      ✍️  Iris Park      - 技术文档
    
    架构模式: 混合模式（生产级推荐）
    默认模型: volcengine/glm-4.7
    
    """
    print(banner)


def check_openclaw():
    """检查 OpenClaw 是否已安装"""
    try:
        result = subprocess.run(
            ["openclaw", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ OpenClaw 已安装: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        print("❌ 错误: 未找到 openclaw 命令")
        print("   请先安装 OpenClaw: npm install -g @openclaw/cli")
        return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def create_workspace_dirs():
    """创建工作区目录"""
    base_path = Path(BASE_WORKSPACE).expanduser()
    base_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 创建工作区目录: {base_path}")
    
    for agent in MUSHTECH_TEAM:
        workspace_name = agent["workspace"]
        workspace_path = Path(workspace_name).expanduser()
        workspace_path.mkdir(parents=True, exist_ok=True)
        print(f"   ✓ {workspace_name}")
    
    return base_path


def create_soul_md(workspace_path: Path, agent: dict):
    """创建 SOUL.md 人格定义文件"""
    name = agent["name"]
    display_name = agent.get("display_name", name.split()[0])
    role = agent["role"]
    emoji = agent.get("emoji", "🦞")
    personality = agent.get("personality", "")
    specialty = agent.get("specialty", "")
    
    soul_content = f"""# SOUL.md - {name} {emoji}

## 身份定位

你是 MushTech 代码外包团队的 **{name}**，大家都叫你 **{display_name}**。

{agent.get('description', '')}

## 性格特点

{personality}

## 专业技能

{specialty}

## 团队角色

"""
    
    if agent.get("type") == "main_brain":
        soul_content += """
## 主脑职责

作为团队的主脑，你需要：

1. **需求分析**：深入理解客户需求，分解为可执行的任务
2. **任务分配**：将任务分配给最合适的专才Agent：
   - 界面设计 → Luna (UI Designer)
   - 代码开发 → Kai (Programmer)
   - 测试验证 → Zoe (Code Tester)
   - 文档编写 → Iris (Document Writer)
3. **进度跟踪**：监控各项任务执行情况
4. **质量把控**：审核专才的产出，确保符合要求
5. **沟通协调**：作为客户和团队的桥梁

## 调度方式

使用 `@agent_id` 向专才分派任务，例如：
```
@mush-dev 请帮我实现用户登录功能
@mush-ui 设计一个简洁的登录页面
```

## 行为准则

- 分配任务时提供完整上下文
- 等待专才完成，不频繁催促
- 整合结果时保持结构化
- 保持技术中立，基于事实决策
- 对团队成员保持尊重和鼓励
"""
    else:
        soul_content += f"""
## 专才职责

作为{role}，你需要：

1. **专业执行**：深耕自己的专业领域
2. **高质量产出**：确保所有交付物符合行业标准
3. **积极沟通**：及时向主脑(Alex)汇报进度和阻碍
4. **协作配合**：与其他专才配合完成复杂任务

## 行为准则

- 接收任务后先进行分析
- 遇到问题及时求助或汇报
- 保持工作区整洁有序
- 定期更新项目进度
- 主动与团队分享知识和经验
"""
    
    soul_path = workspace_path / "SOUL.md"
    soul_path.write_text(soul_content, encoding="utf-8")
    print(f"     写入 SOUL.md")


def update_openclaw_config():
    """更新 openclaw.json 配置（增量更新）"""
    print("\n📝 更新 openclaw.json 配置...")
    
    agent_ids = [agent["id"] for agent in MUSHTECH_TEAM]
    
    # 读取现有配置
    if OPENCLAW_CONFIG_PATH.exists():
        with open(OPENCLAW_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    
    # 确保基本结构存在
    if "agents" not in config:
        config["agents"] = {}
    if "list" not in config["agents"]:
        config["agents"]["list"] = []
    if "defaults" not in config["agents"]:
        config["agents"]["defaults"] = {}
    if "tools" not in config:
        config["tools"] = {}
    if "bindings" not in config:
        config["bindings"] = []
    
    # 更新 defaults.subagents
    config["agents"]["defaults"]["subagents"] = {
        "maxConcurrent": 8,
        "allowlist": agent_ids
    }
    
    # 更新 agents.agentToAgent（全局）
    config["agents"]["agentToAgent"] = {
        "enabled": True,
        "allow": agent_ids,
        "historyLimit": 50
    }
    
    # 更新 tools
    config["tools"]["allow"] = [
        "exec",
        "read",
        "sessions_list",
        "sessions_history",
        "sessions_send",
        "sessions_spawn",
        "session_status"
    ]
    config["tools"]["sessions"] = {
        "visibility": "all"
    }
    config["tools"]["agentToAgent"] = {
        "enabled": True,
        "allow": agent_ids,
        "historyLimit": 50
    }
    
    # 更新或添加每个 agent 的配置
    existing_agent_ids = {a.get("id"): i for i, a in enumerate(config["agents"]["list"])}
    
    for agent in MUSHTECH_TEAM:
        agent_id = agent["id"]
        workspace_path = Path(agent["workspace"]).expanduser()
        agent_dir_path = Path.home() / ".openclaw" / "agents" / agent_id / "agent"
        
        # 其他 agents（排除自己）
        other_agents = [a for a in agent_ids if a != agent_id]
        
        agent_config = {
            "id": agent_id,
            "name": agent.get("name", agent_id),
            "workspace": str(workspace_path),
            "agentDir": str(agent_dir_path),
            "model": agent.get("model", "volcengine/glm-4.7"),
            "identity": {
                "name": agent.get("display_name", agent.get("name", agent_id)),
                "emoji": agent.get("emoji", "🦞")
            },
            "subagents": {
                "maxConcurrent": 8,
                "allowlist": other_agents
            },
            "agentToAgent": {
                "enabled": True,
                "allow": other_agents
            }
        }
        
        if agent_id in existing_agent_ids:
            # 更新现有配置
            idx = existing_agent_ids[agent_id]
            config["agents"]["list"][idx].update(agent_config)
        else:
            # 添加新配置
            config["agents"]["list"].append(agent_config)
    
    # 更新 bindings（feishu channel）
    existing_bindings = {(b.get("agentId"), b.get("match", {}).get("channel")) for b in config["bindings"]}
    for agent in MUSHTECH_TEAM:
        binding_key = (agent["id"], "feishu")
        if binding_key not in existing_bindings:
            config["bindings"].append({
                "agentId": agent["id"],
                "match": {
                    "channel": "feishu"
                }
            })
    
    # 保存配置
    OPENCLAW_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OPENCLAW_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"   ✓ 配置已保存: {OPENCLAW_CONFIG_PATH}")


def create_agents_via_cli():
    """通过CLI创建Agents"""
    print("\n🚀 通过 OpenClaw CLI 创建 Agents...")
    
    for agent in MUSHTECH_TEAM:
        agent_id = agent["id"]
        workspace_path = Path(agent["workspace"]).expanduser()
        agent_dir_path = Path.home() / ".openclaw" / "agents" / agent_id / "agent"
        
        cmd = [
            "openclaw", "agents", "add", agent_id,
            "--json",
            "--non-interactive",
            "--workspace", str(workspace_path),
            "--agent-dir", str(agent_dir_path),
            "--model", agent["model"],
        ]
        
        print(f"   创建 {agent_id}...", end=" ")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print("✓")
                
                # 设置显示名称和emoji
                display_name = agent.get("display_name", agent["name"])
                emoji = agent.get("emoji", "🦞")
                subprocess.run(
                    ["openclaw", "agents", "set-identity", agent_id, 
                     "--name", display_name,
                     "--emoji", emoji],
                    capture_output=True,
                    timeout=10
                )
            else:
                # 可能已经存在
                if "already exists" in result.stderr.lower() or "already exists" in result.stdout.lower():
                    print("✓ (已存在)")
                else:
                    print(f"✗ ({result.stderr[:50]})")
                
        except Exception as e:
            print(f"✗ ({e})")


def restart_gateway():
    """重启 Gateway 以应用新配置"""
    print("\n🔄 重启 Gateway...")
    
    # 停止 gateway
    subprocess.run(["openclaw", "gateway", "stop"], capture_output=True)
    print("   ⏹️  Gateway 已停止")
    
    # 等待一下确保停止
    time.sleep(2)
    
    # 启动 gateway
    result = subprocess.run(
        ["openclaw", "gateway", "start", "--daemon"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("   ✅ Gateway 已启动")
        # 等待 gateway 完全启动
        time.sleep(3)
        return True
    else:
        print(f"   ⚠️  Gateway 启动可能有问题: {result.stderr[:100]}")
        return False


def create_initial_sessions():
    """创建初始 session - 向每个 agent 发送测试消息"""
    print("\n💬 创建初始 sessions...")
    
    for agent in MUSHTECH_TEAM:
        agent_id = agent["id"]
        print(f"   激活 {agent_id}...", end=" ")
        
        # 使用 openclaw sessions send 命令
        result = subprocess.run(
            [
                "openclaw", "sessions", "send",
                "--agent", agent_id,
                "--message", "你好！我是你的团队成员，准备开始协作。"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✓")
        else:
            print(f"⚠️ ({result.stderr[:50]})")
    
    print("   ✅ 初始 sessions 创建完成")


def verify_setup():
    """验证设置"""
    print("\n✅ 验证设置...")
    
    # 检查Agents列表
    try:
        result = subprocess.run(
            ["openclaw", "agents", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            agents = json.loads(result.stdout)
            mush_agents = [a for a in agents if a["id"].startswith("mush-")]
            print(f"   ✓ 已创建 {len(mush_agents)} 个 MushTech Agents")
            for agent in mush_agents:
                print(f"     - {agent.get('id', 'unknown')}: {agent.get('name', 'N/A')}")
    except Exception as e:
        print(f"   ⚠️ 无法验证: {e}")


def print_summary():
    """打印总结"""
    summary = f"""
    🎉 MushTech 团队初始化完成！

    工作区位置: {BASE_WORKSPACE}
    配置文件: {OPENCLAW_CONFIG_PATH}
    
    团队成员:
    """
    
    for agent in MUSHTECH_TEAM:
        emoji = agent.get("emoji", "🦞")
        name = agent["name"]
        display_name = agent.get("display_name", name.split()[0])
        role = agent["role"]
        type_str = "[主脑]" if agent.get("type") == "main_brain" else "[专才]"
        summary += f"      {emoji} {name} ({display_name}) - {role} {type_str}\n"
    
    summary += f"""
    架构模式: 混合模式 (生产级)
    Agent间通信: 已启用
    会话可见性: all
    默认模型: volcengine/glm-4.7
    
    配置内容:
    - 全局 subagents.allowlist: mush-pm, mush-dev, mush-ui, mush-qa, mush-doc
    - 每个 agent 可以访问其他 4 个成员
    - sessions.visibility: all (允许相互查看会话)
    - feishu bindings: 已配置
    
    现在 mush-pm (Alex) 可以:
    - 使用 @mush-dev 调用 Kai
    - 使用 @mush-ui 调用 Luna  
    - 使用 @mush-qa 调用 Zoe
    - 使用 @mush-doc 调用 Iris
    
    下一步:
      1. 确保 Gateway 正在运行
      2. 运行 TUI 应用: ./run.sh
      3. 按 Enter 进入聊天界面
      
    幸福的外包！🐠
    """
    
    print(summary)


def main():
    """主函数"""
    print_banner()
    
    # 检查 OpenClaw
    if not check_openclaw():
        sys.exit(1)
    
    # 创建工作区
    create_workspace_dirs()
    
    # 创建 SOUL.md
    print("\n📝 创建人格定义文件...")
    for agent in MUSHTECH_TEAM:
        workspace_path = Path(agent["workspace"]).expanduser()
        create_soul_md(workspace_path, agent)
    
    # 更新配置（增量更新，保留现有配置）
    update_openclaw_config()
    
    # 通过CLI创建Agents
    create_agents_via_cli()
    
    # 重启 Gateway
    restart_gateway()
    
    # 创建初始 sessions
    create_initial_sessions()
    
    # 验证
    verify_setup()
    
    # 总结
    print_summary()


if __name__ == "__main__":
    main()
