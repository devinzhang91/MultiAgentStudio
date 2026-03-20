"""Agent 初始化与默认文档引导。"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request

from .cmd_executor import get_cmd_executor
from .config_manager import get_config_manager, StudioConfig
from .logger import logger
from .models import Employee
from .templates.base import AgentConfig

# 预定义的 Agent ID 列表
SLIDEV_AGENT_IDS = frozenset([
    "ppt-director",
    "ppt-content-architect",
    "ppt-visual-designer",
    "ppt-code-specialist",
    "ppt-integrator",
    "ppt-image-artist"
])

REMOTION_AGENT_IDS = frozenset([
    "video-director",
    "video-script-writer",
    "remotion-core-dev",
    "remotion-media-dev",
    "video-quality-analyst"
])


class HookClient:
    """OpenClaw Hook API 客户端"""
    
    OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
    
    def __init__(self, studio_config: Optional[StudioConfig] = None):
        self.studio_config = studio_config or get_config_manager().get_config()
    
    def get_endpoint(self) -> Tuple[str, str]:
        """读取当前hooks配置并构建Agent Hook地址"""
        with open(self.OPENCLAW_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        hooks = config.get("hooks", {}) if isinstance(config, dict) else {}
        hook_path = str(hooks.get("path") or "/hooks").strip() or "/hooks"
        if not hook_path.startswith("/"):
            hook_path = f"/{hook_path}"
        hook_path = hook_path.rstrip("/")
        hook_token = str(hooks.get("token") or "").strip()
        endpoint = f"{self.studio_config.gateway_url}{hook_path}/agent"
        return endpoint, hook_token

    def post_message(self, endpoint: str, token: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """通过OpenClaw Hook向指定Agent发送消息"""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["x-openclaw-token"] = token

        last_error = "unknown error"
        for attempt in range(12):
            try:
                req = urllib_request.Request(
                    endpoint,
                    data=body,
                    headers=headers,
                    method="POST",
                )
                with urllib_request.urlopen(req, timeout=10) as response:
                    raw = response.read().decode("utf-8") or "{}"
                    data = json.loads(raw)
                    if isinstance(data, dict) and data.get("ok") is True:
                        return True, ""
                    last_error = str(data.get("error") if isinstance(data, dict) else raw)
            except urllib_error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")
                last_error = f"HTTP {exc.code}: {detail or exc.reason}"
            except Exception as exc:
                last_error = str(exc)

            if attempt < 11:
                time.sleep(1.5)

        return False, last_error

    def send_to_agent(self, agent_id: str, session_key: str, message: str, name: str = "MushTech Message") -> Tuple[bool, str]:
        """发送消息到指定Agent的便捷方法"""
        endpoint, token = self.get_endpoint()
        payload = {
            "name": name,
            "agentId": agent_id,
            "sessionKey": session_key,
            "message": message,
        }
        return self.post_message(endpoint, token, payload)


def setup_slidev_skills_for_agent(
    agent_id: str,
    workspace: str,
) -> Tuple[bool, str]:
    """
    为Agent部署Slidev skills（离线预置）
    
    Skills预置在 data/agents-docs/slidev_ppt/{agent_id}/skills/ 目录下
    
    Args:
        agent_id: Agent ID
        workspace: 工作空间路径
    
    Returns:
        (success, message)
    """
    from .templates.slidev_ppt import SlidevPPTTemplate
    
    template = SlidevPPTTemplate()
    return template.deploy_skills_for_agent(agent_id, workspace)


def setup_slidev_skills_for_team(workspace_map: Dict[str, str]) -> Dict[str, Tuple[bool, str]]:
    """
    为整个PPT团队部署skills
    
    Args:
        workspace_map: Agent ID到工作空间的映射
        
    Returns:
        各Agent的部署结果
    """
    from .templates.slidev_ppt import SlidevPPTTemplate
    
    template = SlidevPPTTemplate()
    return template.deploy_all_skills(workspace_map)


def setup_remotion_skills_for_agent(
    agent_id: str,
    workspace: str,
) -> Tuple[bool, str]:
    """
    为Agent部署Remotion skills（离线预置）
    
    Skills预置在 data/agents-docs/remotion_video/{agent_id}/skills/ 目录下
    
    Args:
        agent_id: Agent ID
        workspace: 工作空间路径
    
    Returns:
        (success, message)
    """
    from .templates.remotion_video import RemotionVideoTemplate
    
    template = RemotionVideoTemplate()
    return template.deploy_skills_for_agent(agent_id, workspace)


def setup_remotion_skills_for_team(workspace_map: Dict[str, str]) -> Dict[str, Tuple[bool, str]]:
    """
    为整个Remotion视频团队部署skills
    
    Args:
        workspace_map: Agent ID到工作空间的映射
        
    Returns:
        各Agent的部署结果
    """
    from .templates.remotion_video import RemotionVideoTemplate
    
    template = RemotionVideoTemplate()
    return template.deploy_all_skills(workspace_map)


class AgentInitializer:
    """通过文件拷贝初始化 agent 默认文档。"""

    # 模板ID到agents-docs目录的映射
    TEMPLATE_MAPPING = {
        "slidev_ppt": "slidev_ppt",
        "remotion_video": "remotion_video", 
        "software_engineering": "software_engineering",
        "stock_analysis": "stock_analysis",
    }

    def __init__(self):
        self.studio_config = get_config_manager().get_config()
        self.cmd = get_cmd_executor()
        self.hook_client = HookClient(self.studio_config)
        self.prompts_dir = Path(__file__).parent / "templates" / "prompts"
        self.agents_docs_dir = Path(__file__).parent.parent / "data" / "agents-docs"
        self._shared_user_profile = self._load_shared_user_profile()
    
    def _copy_agent_docs(self, agent_id: str, template_id: str, workspace: str) -> Tuple[bool, str]:
        """
        拷贝agent的markdown文档到工作空间
        
        Args:
            agent_id: Agent ID
            template_id: 模板ID (如 slidev_ppt)
            workspace: 工作空间路径
            
        Returns:
            (success, message)
        """
        # 获取模板对应的docs目录名
        docs_template = self.TEMPLATE_MAPPING.get(template_id, template_id)
        source_dir = self.agents_docs_dir / docs_template / agent_id
        
        if not source_dir.exists():
            # 尝试查找其他模板目录
            found = False
            for tmpl_dir in self.agents_docs_dir.iterdir():
                if tmpl_dir.is_dir():
                    alt_source = tmpl_dir / agent_id
                    if alt_source.exists():
                        source_dir = alt_source
                        found = True
                        break
            if not found:
                return False, f"Agent文档目录不存在: {source_dir}"
        
        workspace_path = Path(workspace).expanduser()
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        required_files = ["SOUL.md", "AGENTS.md", "IDENTITY.md", "USER.md"]
        copied_count = 0
        errors = []
        
        for filename in required_files:
            source_file = source_dir / filename
            if source_file.exists():
                try:
                    dest_file = workspace_path / filename
                    shutil.copy2(source_file, dest_file)
                    copied_count += 1
                except Exception as e:
                    errors.append(f"{filename}: {e}")
            else:
                errors.append(f"{filename}: 文件不存在")
        
        if copied_count == len(required_files):
            return True, f"已拷贝 {copied_count} 个文档到 {workspace_path}"
        elif copied_count > 0:
            return True, f"已拷贝 {copied_count}/{len(required_files)} 个文档，警告: {'; '.join(errors)}"
        else:
            return False, f"拷贝失败: {'; '.join(errors)}"

    def initialize_agent(
        self,
        agent: AgentConfig,
        *,
        workspace: str,
        reset_after_bootstrap: bool = True,
        setup_skills: bool = True,
        template_id: str = "",
    ) -> Tuple[bool, str]:
        # 如果是PPT团队成员，自动部署Slidev skills（离线）
        if setup_skills and agent.id in SLIDEV_AGENT_IDS:
            logger.info(f"Deploying Slidev skills for {agent.id}...")
            skills_ok, skills_msg = setup_slidev_skills_for_agent(
                agent_id=agent.id,
                workspace=workspace,
            )
            if skills_ok:
                logger.info(f"Skills deployed: {skills_msg}")
            else:
                logger.warning(f"Skills deployment failed: {skills_msg}")
        
        # 如果是Remotion视频工作室成员，自动部署Remotion skills（离线）
        if setup_skills and agent.id in REMOTION_AGENT_IDS:
            logger.info(f"Deploying Remotion skills for {agent.id}...")
            skills_ok, skills_msg = setup_remotion_skills_for_agent(
                agent_id=agent.id,
                workspace=workspace,
            )
            if skills_ok:
                logger.info(f"Skills deployed: {skills_msg}")
            else:
                logger.warning(f"Skills deployment failed: {skills_msg}")
        
        # 拷贝agent文档（新的文件拷贝方式）
        logger.info(f"Copying agent docs for {agent.id}...")
        docs_ok, docs_msg = self._copy_agent_docs(agent.id, template_id, workspace)
        if docs_ok:
            logger.info(f"Agent docs copied: {docs_msg}")
        else:
            logger.warning(f"Agent docs copy failed: {docs_msg}")
            # 如果拷贝失败，回退到旧的消息方式
            logger.info(f"Falling back to hook message for {agent.id}")
            message = self.build_bootstrap_message_for_agent(agent)
            return self._bootstrap_and_optionally_reset(
                agent_id=agent.id,
                session_key=f"agent:{agent.id}:main",
                workspace=workspace,
                identity_name=agent.name,
                identity_emoji=agent.emoji,
                message=message,
                reset_after_bootstrap=reset_after_bootstrap,
                name=f"MushTech Studio Bootstrap - {agent.display_name}",
            )
        
        # 设置身份并可选重置会话
        sync_ok, sync_reason = self.cmd.agents_set_identity(
            agent.id,
            name=agent.name,
            emoji=agent.emoji,
        )
        if not sync_ok:
            return False, sync_reason
        
        if reset_after_bootstrap:
            time.sleep(1.0)
            return self.reset_session(agent.id, f"agent:{agent.id}:main")
        
        return True, docs_msg

    def initialize_employee(self, employee: Employee, *, reset_after_bootstrap: bool = True) -> Tuple[bool, str]:
        message = self.build_bootstrap_message_for_employee(employee)
        return self._bootstrap_and_optionally_reset(
            agent_id=employee.agent_id,
            session_key=employee.session_key or f"agent:{employee.agent_id}:main",
            workspace=employee.workspace,
            identity_name=employee.name,
            identity_emoji=employee.emoji,
            message=message,
            reset_after_bootstrap=reset_after_bootstrap,
            name=f"MushTech Studio Bootstrap - {employee.display_name or employee.name}",
        )

    def reset_session(self, agent_id: str, session_key: str) -> Tuple[bool, str]:
        return self.hook_client.send_to_agent(
            agent_id=agent_id,
            session_key=session_key,
            message="/new",
            name="MushTech Studio Session Reset",
        )

    def build_bootstrap_message_for_agent(self, agent: AgentConfig) -> str:
        docs = agent.bootstrap_docs or {}
        soul_md = self._render_soul_md(
            name=agent.name,
            display_name=agent.display_name,
            role=agent.role,
            emoji=agent.emoji,
            personality=agent.personality,
            specialty=agent.specialty,
            doc=docs.get("soul", {}),
        )
        agents_md = self._render_agents_md(
            role=agent.role,
            display_name=agent.display_name,
            doc=docs.get("agents", {}),
        )
        identity_md = self._render_identity_md(
            name=agent.name,
            display_name=agent.display_name,
            role=agent.role,
            emoji=agent.emoji,
            doc=docs.get("identity", {}),
        )
        user_md = self._render_user_md()
        return self._compose_bootstrap_message(agent.display_name, soul_md, agents_md, identity_md, user_md)

    def build_bootstrap_message_for_employee(self, employee: Employee) -> str:
        default_traits = employee.personality or f"你是 {employee.role}，非常自主、执行力强、可靠，并且有鲜明的个人风格。"
        soul_md = self._render_soul_md(
            name=employee.name,
            display_name=employee.display_name or employee.name,
            role=employee.role,
            emoji=employee.emoji,
            personality=default_traits,
            specialty=employee.specialty or employee.role,
            doc={
                "mission": f"围绕 {employee.role} 的职责独立完成任务，并主动交付高质量结果。",
                "voice": "专业、自主、坦诚、结果导向。",
                "traits": ["自主推进", "按结果负责", "善于沟通", "有边界感", "富有个性"],
                "rules": ["先理解任务目标，再动手执行。", "发现风险时主动提出备选方案。", "输出结果时附上假设、边界和下一步建议。"],
            },
        )
        agents_md = self._render_agents_md(
            role=employee.role,
            display_name=employee.display_name or employee.name,
            doc={
                "objective": f"负责 {employee.role} 范围内的专业执行与结果交付。",
                "workflow": ["澄清目标", "制定方案", "执行并自检", "汇报结果与风险"],
                "forbidden": ["不要无依据承诺。", "不要跳过验证。", "不要越过职责边界替他人拍板。"],
            },
        )
        identity_md = self._render_identity_md(
            name=employee.name,
            display_name=employee.display_name or employee.name,
            role=employee.role,
            emoji=employee.emoji,
            doc={
                "boundary": f"你的工作边界是 {employee.role} 的专业职责，跨域协作时要先说明依赖与假设。",
                "tagline": "先独立推进，再主动协同。",
            },
        )
        user_md = self._render_user_md()
        return self._compose_bootstrap_message(employee.display_name or employee.name, soul_md, agents_md, identity_md, user_md)

    def _bootstrap_and_optionally_reset(
        self,
        *,
        agent_id: str,
        session_key: str,
        workspace: str,
        identity_name: str,
        identity_emoji: str,
        message: str,
        reset_after_bootstrap: bool,
        name: str,
    ) -> Tuple[bool, str]:
        ok, reason = self.hook_client.send_to_agent(
            agent_id=agent_id,
            session_key=session_key,
            message=message,
            name=name,
        )
        if not ok:
            return False, reason

        sync_ok, sync_reason = self.cmd.agents_set_identity(
            agent_id,
            name=identity_name,
            emoji=identity_emoji,
        )
        if not sync_ok:
            return False, sync_reason

        if reset_after_bootstrap:
            time.sleep(1.0)
            return self.reset_session(agent_id, session_key)

        return True, ""

    def _load_shared_user_profile(self) -> Dict[str, Any]:
        path = self.prompts_dir / "shared_user.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _compose_bootstrap_message(
        self,
        display_name: str,
        soul_md: str,
        agents_md: str,
        identity_md: str,
        user_md: str,
    ) -> str:
        return f"""你现在要完成一项初始化任务。

请在你的 workspace 根目录中创建或覆盖以下四个文件：`SOUL.md`、`AGENTS.md`、`IDENTITY.md`、`USER.md`。
要求：
1. 直接写文件，不要只讨论。
2. 保留文件名与整体职责边界。
3. 允许你做非常轻微的措辞优化，但不能改变核心职责、边界、合作方式。
4. 完成后，只回复一行：DONE: SOUL.md, AGENTS.md, IDENTITY.md, USER.md

以下是默认内容，请据此落盘：

===== SOUL.md =====
{soul_md}

===== AGENTS.md =====
{agents_md}

===== IDENTITY.md =====
{identity_md}

===== USER.md =====
{user_md}

请开始执行，{display_name}。"""

    def _render_soul_md(
        self,
        *,
        name: str,
        display_name: str,
        role: str,
        emoji: str,
        personality: str,
        specialty: str,
        doc: Dict[str, Any],
    ) -> str:
        traits = "\n".join(f"- {item}" for item in doc.get("traits", []))
        rules = "\n".join(f"- {item}" for item in doc.get("rules", []))
        team_values = self._render_list_section("## 团队协作信条", doc.get("team_values", []))
        question_rules = self._render_list_section("## 遇到不明细节时", doc.get("question_rules", []))
        return f"""# SOUL.md - {name} {emoji}

## 我是谁

我是 **{name}**，团队通常叫我 **{display_name}**。
我的岗位是：**{role}**。
我的核心使命：{doc.get('mission', specialty)}

## 性格与气质

{doc.get('voice', personality)}

{personality}

## 我的关键特质

{traits}

## 我的工作原则

{rules}

{team_values}

{question_rules}

## 我的专业重点

{specialty}
"""

    def _render_agents_md(self, *, role: str, display_name: str, doc: Dict[str, Any]) -> str:
        workflow = "\n".join(f"{idx}. {item}" for idx, item in enumerate(doc.get("workflow", []), start=1))
        forbidden = "\n".join(f"- {item}" for item in doc.get("forbidden", []))
        collaboration = self._render_list_section("## 协作要求", doc.get("collaboration", []))
        tools_and_skills = self._render_list_section("## Tools / Skills 使用原则", doc.get("tools_and_skills", []))
        clarification = self._render_list_section("## 澄清与追问机制", doc.get("clarification", []))
        review = self._render_list_section("## 进度与复核机制", doc.get("review", []))
        return f"""# AGENTS.md - {display_name}

## 职责目标

{doc.get('objective', role)}

## 标准工作流程（SOP）

{workflow}

## 工作守则

- 结果优先，但必须说明依据和边界。
- 需要协作时主动同步上下文，不让别人猜。
- 输出尽量结构化，便于复用与审阅。

{collaboration}

{tools_and_skills}

{clarification}

{review}

## 禁区

{forbidden}
"""

    def _render_identity_md(
        self,
        *,
        name: str,
        display_name: str,
        role: str,
        emoji: str,
        doc: Dict[str, Any],
    ) -> str:
        return f"""# IDENTITY.md - {display_name}

_由团队默认生成，你可以微调，但不要丢失身份边界。_

- **Name:** {name}
- **Display Name:** {display_name}
- **Role:** {role}
- **Vibe:** 专业、自主、有个性、结果导向
- **Emoji:** {emoji}
- **Avatar:**
    _(workspace-relative path, http(s) URL, or data URI; optional)_

## 个体宣言

{doc.get('tagline', '')}

## 工作边界

{doc.get('boundary', '')}

## 对外形象

保持专业、主动、有个性；不卑不亢，不装懂，不失控。
"""

    def _render_list_section(self, title: str, items: list[str]) -> str:
        if not items:
            return ""
        body = "\n".join(f"- {item}" for item in items)
        return f"{title}\n\n{body}"

    def _render_user_md(self) -> str:
        style = "\n".join(f"- {item}" for item in self._shared_user_profile.get("collaboration_style", []))
        dont = "\n".join(f"- {item}" for item in self._shared_user_profile.get("do_not", []))
        success = "\n".join(f"- {item}" for item in self._shared_user_profile.get("success_definition", []))
        return f"""# USER.md

## 用户角色

- Role: {self._shared_user_profile.get('role_name')}
- Identity: {self._shared_user_profile.get('identity')}
- Goal: {self._shared_user_profile.get('goal')}

## 协作方式

{style}

## 不要做什么

{dont}

## 成功标准

{success}
"""
