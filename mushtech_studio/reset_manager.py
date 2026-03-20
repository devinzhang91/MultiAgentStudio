"""
重置管理器
处理reset命令的完整逻辑：
1. 备份并重置openclaw.json
2. 重置mushtech_studio配置
3. 执行openclaw gateway restart
"""

import json
import secrets
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional

from .agent_initializer import AgentInitializer, HookClient
from .cmd_executor import get_cmd_executor
from .config_manager import get_config_manager
from .templates import get_template
from .logger import logger


class ResetManager:
    """重置管理器"""
    
    OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.studio_config = self.config_manager.get_config()
        self.cmd = get_cmd_executor()
        self.initializer = AgentInitializer()
        self.hook_client = HookClient(self.studio_config)

    def _get_backup_dir(self) -> Path:
        """统一返回工作室备份目录。"""
        return Path(self.studio_config.base_workspace).expanduser() / "backups"
    
    def reset(self, force: bool = False) -> Tuple[bool, str]:
        """
        执行重置流程
        
        Args:
            force: 是否强制重置（跳过确认）
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            logger.info("[ResetManager] 开始重置流程")
            
            # 1. 验证openclaw.json存在
            if not self.OPENCLAW_CONFIG_PATH.exists():
                return False, f"未找到OpenClaw配置文件: {self.OPENCLAW_CONFIG_PATH}"
            
            # 2. 备份当前配置
            backup_path = self._backup_openclaw_config()
            logger.info(f"[ResetManager] 配置已备份到: {backup_path}")

            # 2.5 归档旧 workspace 并删除旧 agents
            self._archive_previous_workspace()
            self._delete_existing_agents()
            
            # 3. 获取模板
            template = get_template(self.studio_config.studio_type)
            logger.info(f"[ResetManager] 使用模板: {template.name}")
            
            # 4. 更新openclaw.json
            success = self._update_openclaw_json(template)
            if not success:
                return False, "更新openclaw.json失败"
            logger.info("[ResetManager] openclaw.json已更新")

            # 4.1 确保运行目录存在
            success = self._ensure_runtime_directories(template)
            if not success:
                return False, "初始化Workspace和Agent目录失败"
            logger.info("[ResetManager] Workspace和Agent目录已准备完成")

            # 4.2 使用 openclaw CLI 创建默认 agents
            success, failures = self._create_agents_from_template(template)
            if not success:
                return False, f"创建默认Agent失败: {'; '.join(failures)}"
            logger.info("[ResetManager] 默认 agents 已通过 openclaw 创建")
            
            # 5. 重置employees.json
            success = self._reset_employees_json(template)
            if not success:
                return False, "重置employees.json失败"
            logger.info("[ResetManager] employees.json已重置")
            
            # 6. 重置multi_agent_config.json
            success = self._reset_multi_agent_config(template)
            if not success:
                return False, "重置multi_agent_config.json失败"
            logger.info("[ResetManager] multi_agent_config.json已重置")
            
            # 7. 删除聊天记录
            deleted_count = self._delete_message_history()
            logger.info(f"[ResetManager] 已删除 {deleted_count} 个聊天记录文件")
            
            # 7.5 设置 OpenClaw 默认超时时间为 1800 秒（30分钟）
            success, message = self._set_default_timeout()
            if not success:
                logger.warning(f"[ResetManager] 设置默认超时时间失败: {message}")
            else:
                logger.info(f"[ResetManager] {message}")
            
            # 8. 执行gateway restart
            success, message = self._restart_gateway()
            if not success:
                return False, f"重启Gateway失败: {message}"
            logger.info("[ResetManager] Gateway已重启")

            # 9. 引导每位员工写入默认 Markdown，并在结束后发送 /new
            refreshed_count, failures = self._bootstrap_template_agents(template)
            logger.info(
                f"[ResetManager] 已完成 {refreshed_count} 个员工初始化引导，失败 {len(failures)} 个"
            )

            summary = (
                f"重置完成！OpenClaw Gateway已重启，"
                f"并已完成 {refreshed_count}/{len(template.get_agents())} 个员工的默认文件初始化与会话重建。"
            )
            if failures:
                summary += f" 失败会话: {'; '.join(failures)}"
            
            return True, summary
            
        except Exception as e:
            logger.exception("[ResetManager] 重置过程中发生错误")
            return False, f"重置失败: {str(e)}"
    
    def _backup_openclaw_config(self) -> Path:
        """
        备份openclaw.json
        
        Returns:
            Path: 备份文件路径
        """
        # 创建备份目录
        backup_dir = self._get_backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"openclaw.json.bak.{timestamp}"
        backup_path = backup_dir / backup_filename
        
        # 复制文件
        shutil.copy2(self.OPENCLAW_CONFIG_PATH, backup_path)
        
        return backup_path

    def _get_dm_scope(self) -> str:
        """根据当前架构返回会话范围"""
        if self.studio_config.architecture == "decentralized":
            return "per-peer"
        return "main"

    def _resolve_gateway_bind(self) -> Tuple[str, Optional[str]]:
        """根据配置的Gateway IP生成OpenClaw绑定方式"""
        host = (self.studio_config.gateway_host or "").strip().lower()
        if host in {"", "127.0.0.1", "localhost", "::1"}:
            return "loopback", None
        return "custom", self.studio_config.gateway_host.strip()

    def _rebuild_bindings(self, existing_bindings: Any, agent_ids: List[str]) -> List[Dict[str, Any]]:
        """基于现有绑定模板重建当前团队的bindings"""
        if not isinstance(existing_bindings, list):
            return []

        binding_templates: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for binding in existing_bindings:
            if not isinstance(binding, dict):
                continue
            template = {k: v for k, v in binding.items() if k != "agentId"}
            if not template:
                continue
            key = json.dumps(template, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            binding_templates.append(template)

        rebuilt: List[Dict[str, Any]] = []
        for template in binding_templates:
            for agent_id in agent_ids:
                binding = json.loads(json.dumps(template, ensure_ascii=False))
                binding["agentId"] = agent_id
                rebuilt.append(binding)

        return rebuilt

    def _read_local_gateway_token(self, config: Optional[Dict[str, Any]] = None) -> str:
        """读取本地 Gateway 鉴权 token，优先 gateway.auth.token，其次 hooks.token。"""
        try:
            if config is None:
                with open(self.OPENCLAW_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            gateway = config.get("gateway", {}) if isinstance(config, dict) else {}
            auth = gateway.get("auth", {}) if isinstance(gateway, dict) else {}
            gateway_token = str(auth.get("token") or "").strip()
            if gateway_token:
                return gateway_token

            hooks = config.get("hooks", {}) if isinstance(config, dict) else {}
            return str(hooks.get("token") or "").strip()
        except Exception:
            return ""
    
    def _update_openclaw_json(self, template) -> bool:
        """
        更新openclaw.json文件
        
        Args:
            template: 工作室模板
            
        Returns:
            bool: 是否成功
        """
        try:
            # 读取当前配置
            with open(self.OPENCLAW_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 确保agents部分存在
            if "agents" not in config:
                config["agents"] = {}

            if "meta" not in config:
                config["meta"] = {}
            config["meta"]["lastTouchedAt"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            
            # 获取当前模板的 agent ids，用于更新全局权限与 hooks
            base_workspace = self.studio_config.base_workspace
            agent_ids = [a.id for a in template.get_agents()]

            # agents.list 交由 openclaw agents add 逐个创建
            config["agents"]["list"] = []

            defaults = config["agents"].setdefault("defaults", {})
            defaults["workspace"] = f"{base_workspace}/workspace"

            bind_mode, custom_bind_host = self._resolve_gateway_bind()
            gateway = config.setdefault("gateway", {})
            gateway["port"] = self.studio_config.gateway_port
            gateway["bind"] = bind_mode
            if custom_bind_host:
                gateway["customBindHost"] = custom_bind_host
            else:
                gateway.pop("customBindHost", None)

            auth = gateway.setdefault("auth", {})
            auth["mode"] = "token"

            hooks = config.setdefault("hooks", {})
            hooks["enabled"] = True
            hooks["path"] = hooks.get("path") or "/hooks"
            hooks["token"] = hooks.get("token") or secrets.token_hex(24)
            hooks["allowRequestSessionKey"] = True
            hooks["allowedAgentIds"] = agent_ids
            hooks["allowedSessionKeyPrefixes"] = ["agent:", "hook:"]

            tools = config.setdefault("tools", {})
            agent_to_agent = tools.setdefault("agentToAgent", {})
            agent_to_agent["enabled"] = True
            agent_to_agent["allow"] = agent_ids

            session = config.setdefault("session", {})
            session["dmScope"] = self._get_dm_scope()

            config["bindings"] = self._rebuild_bindings(config.get("bindings"), agent_ids)
            
            # 写入更新后的配置
            with open(self.OPENCLAW_CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"[ResetManager] 更新openclaw.json失败: {e}")
            return False

    def _ensure_runtime_directories(self, template) -> bool:
        """确保workspace和agent目录存在"""
        try:
            base_workspace = Path(self.studio_config.base_workspace).expanduser()
            base_workspace.mkdir(parents=True, exist_ok=True)

            agents = template.get_openclaw_agents_config(
                self.studio_config.base_workspace,
                self.studio_config.architecture,
            )
            for agent in agents:
                workspace = Path(str(agent.get("workspace", ""))).expanduser()
                agent_dir = Path(str(agent.get("agentDir", ""))).expanduser()
                if str(workspace):
                    workspace.mkdir(parents=True, exist_ok=True)
                if str(agent_dir):
                    agent_dir.mkdir(parents=True, exist_ok=True)

            return True
        except Exception as e:
            logger.error(f"[ResetManager] 初始化运行目录失败: {e}")
            return False

    def _archive_previous_workspace(self) -> bool:
        try:
            base_workspace = Path(self.studio_config.base_workspace).expanduser()
            workspace_root = base_workspace / "workspace"
            if not workspace_root.exists():
                return True

            backup_dir = self._get_backup_dir()
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = backup_dir / f"workspace_backup_{timestamp}"

            shutil.make_archive(str(archive_name), "zip", root_dir=str(workspace_root))
            logger.info(f"[ResetManager] 归档旧 workspace 到: {archive_name}.zip")

            shutil.rmtree(workspace_root, ignore_errors=True)
            logger.info(f"[ResetManager] 清理旧 workspace 目录: {workspace_root}")

            return True
        except Exception as e:
            logger.warning(f"[ResetManager] 归档 workspace 失败: {e}")
            return False

    def _gather_existing_agent_ids(self) -> List[str]:
        data_dir = Path(__file__).parent.parent / "data"
        employees_file = data_dir / "employees.json"
        agent_ids: List[str] = []

        if not employees_file.exists():
            return agent_ids

        try:
            payload = json.loads(employees_file.read_text(encoding="utf-8"))
        except Exception:
            return agent_ids

        for key, value in payload.items():
            if not isinstance(value, dict):
                continue
            agent_id = value.get("agent_id")
            if agent_id and agent_id not in agent_ids:
                agent_ids.append(agent_id)

        return agent_ids

    def _delete_existing_agents(self) -> bool:
        agent_ids = self._gather_existing_agent_ids()
        if not agent_ids:
            return True

        failures: List[str] = []
        for agent_id in agent_ids:
            success, _ = self.cmd.agents_delete(agent_id, force=True)
            if not success:
                failures.append(agent_id)

        if failures:
            logger.warning(f"[ResetManager] 删除 agents 失败: {failures}")
        else:
            logger.info(f"[ResetManager] 删除旧 agents: {agent_ids}")

        return not failures

    def _create_agents_from_template(self, template) -> Tuple[bool, List[str]]:
        failures: List[str] = []
        workspace_map = template.get_workspace_map(
            self.studio_config.base_workspace,
            self.studio_config.architecture,
        )

        for agent in template.get_agents():
            workspace = workspace_map.get(agent.id, f"{self.studio_config.base_workspace}/workspace/{agent.id}")
            agent_dir = f"~/.openclaw/agents/{agent.id}/agent"

            success, payload = self.cmd.agents_add(
                name=agent.id,
                workspace=workspace,
                agent_dir=agent_dir,
                model=agent.model,
                non_interactive=True,
            )
            if not success:
                failures.append(f"{agent.id}({payload.get('error', 'add failed')})")
                continue

            identity_ok, identity_reason = self.cmd.agents_set_identity(
                agent.id,
                name=agent.display_name or agent.name,
                emoji=agent.emoji,
            )
            if not identity_ok:
                failures.append(f"{agent.id}(identity: {identity_reason})")
            elif agent.is_main_brain:
                bind_channel, bind_account = self._get_main_brain_binding()
                bind_ok, bind_reason = self.cmd.agents_bind(agent.id, bind_channel, bind_account)
                if not bind_ok:
                    failures.append(f"{agent.id}(bind: {bind_reason})")

        return not failures, failures
    
    def _get_main_brain_binding(self) -> Tuple[str, Optional[str]]:
        """返回重启时主脑的 channel binding 配置"""
        channel = (self.studio_config.main_brain_bind_channel or "").strip()
        if not channel:
            channel = "feishu"
        account = (self.studio_config.main_brain_bind_account_id or "").strip()
        return channel, account or None

    def _reset_employees_json(self, template) -> bool:
        """
        重置employees.json
        
        Args:
            template: 工作室模板
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取员工配置
            base_workspace = self.studio_config.base_workspace
            employees = template.get_employees_config(
                base_workspace,
                self.studio_config.architecture,
            )
            
            # 构建保存数据
            runtime_token = self._read_local_gateway_token()
            data = {
                "_openclaw_config": {
                    "base_url": self.studio_config.gateway_url,
                    "token": runtime_token,
                    "timeout": 120
                }
            }
            
            for emp in employees:
                emp_id = emp["id"]
                data[emp_id] = emp
            
            # 保存到文件
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            employees_file = data_dir / "employees.json"
            
            with open(employees_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"[ResetManager] 重置employees.json失败: {e}")
            return False
    
    def _reset_multi_agent_config(self, template) -> bool:
        """
        重置multi_agent_config.json
        
        Args:
            template: 工作室模板
            
        Returns:
            bool: 是否成功
        """
        try:
            agents = template.get_agents()
            agent_ids = [a.id for a in agents]
            
            # 找到主脑和专才
            main_brain = None
            specialists = []

            if self.studio_config.architecture == "decentralized":
                specialists = [agent.to_dict() for agent in agents]
            else:
                for agent in agents:
                    if agent.is_main_brain:
                        main_brain = agent.to_dict()
                    else:
                        specialists.append(agent.to_dict())
            
            config = {
                "enabled": True,
                "mode": self.studio_config.architecture,
                "agent_to_agent_enabled": True,
                "allowed_agents": agent_ids,
                "dm_scope": self._get_dm_scope(),
                "base_workspace": self.studio_config.base_workspace,
                "default_model": "volcengine/glm-4.7",
                "main_brain": main_brain or {},
                "specialists": specialists
            }
            
            # 保存到文件
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            config_file = data_dir / "multi_agent_config.json"
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"[ResetManager] 重置multi_agent_config.json失败: {e}")
            return False
    
    def _delete_message_history(self) -> int:
        """
        删除聊天记录文件 (data/messages_*.jsonl)
        
        Returns:
            int: 删除的文件数量
        """
        try:
            data_dir = Path(__file__).parent.parent / "data"
            if not data_dir.exists():
                return 0
            
            deleted_count = 0
            
            # 查找并删除 messages_*.jsonl 文件
            for msg_file in data_dir.glob("messages_*.jsonl"):
                try:
                    msg_file.unlink()
                    deleted_count += 1
                    logger.info(f"[ResetManager] 删除聊天记录: {msg_file.name}")
                except Exception as e:
                    logger.warning(f"[ResetManager] 删除聊天记录失败 {msg_file.name}: {e}")
            
            # 同时删除旧的 messages.json 文件（如果存在）
            old_msg_file = data_dir / "messages.json"
            if old_msg_file.exists():
                try:
                    old_msg_file.unlink()
                    deleted_count += 1
                    logger.info(f"[ResetManager] 删除旧聊天记录: {old_msg_file.name}")
                except Exception as e:
                    logger.warning(f"[ResetManager] 删除旧聊天记录失败 {old_msg_file.name}: {e}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"[ResetManager] 删除聊天记录时出错: {e}")
            return 0

    def _bootstrap_template_agents(self, template) -> Tuple[int, List[str]]:
        """重启后引导所有 Agent 写入默认 Markdown，并在最后发送 /new。"""
        try:
            refreshed_count = 0
            failures: List[str] = []
            workspace_map = template.get_workspace_map(
                self.studio_config.base_workspace,
                self.studio_config.architecture,
            )
            
            # 获取当前工作室类型作为template_id
            template_id = self.studio_config.studio_type

            for agent in template.get_agents():
                success, reason = self.initializer.initialize_agent(
                    agent,
                    workspace=workspace_map.get(agent.id, f"{self.studio_config.base_workspace}/workspace/{agent.id}"),
                    reset_after_bootstrap=True,
                    template_id=template_id,
                )
                if success:
                    refreshed_count += 1
                else:
                    failures.append(f"{agent.id}({reason})")

            return refreshed_count, failures
        except Exception as e:
            logger.error(f"[ResetManager] 初始化默认 Markdown 失败: {e}")
            return 0, [str(e)]
    
    def _set_default_timeout(self) -> Tuple[bool, str]:
        """
        设置 OpenClaw 默认超时时间为 1800 秒（30分钟）
        
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            return self.cmd.config_set("agents.defaults.timeoutSeconds", 1800)
        except Exception as e:
            logger.error(f"[ResetManager] 设置默认超时时间失败: {e}")
            return False, str(e)
    
    def _restart_gateway(self) -> Tuple[bool, str]:
        """
        执行openclaw gateway restart
        
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            result = subprocess.run(
                ["openclaw", "gateway", "restart"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return True, result.stdout or "Gateway重启成功"
            else:
                return False, result.stderr or "Gateway重启失败"
                
        except subprocess.TimeoutExpired:
            return False, "Gateway重启超时"
        except FileNotFoundError:
            return False, "未找到openclaw命令，请确保OpenClaw CLI已安装"
        except Exception as e:
            return False, f"执行重启命令失败: {str(e)}"
    
    def get_reset_preview(self) -> Dict[str, Any]:
        """
        获取重置预览信息
        
        Returns:
            Dict: 预览信息
        """
        template = get_template(self.studio_config.studio_type)
        agents = template.get_agents()
        
        return {
            "studio_type": template.name,
            "architecture": self.studio_config.get_architecture_display_name(),
            "workspace": self.studio_config.base_workspace,
            "agents_count": len(agents),
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "role": a.role,
                    "emoji": a.emoji
                }
                for a in agents
            ]
        }


def run_reset(force: bool = False) -> Tuple[bool, str]:
    """
    执行重置命令
    
    Args:
        force: 是否强制重置
        
    Returns:
        Tuple[bool, str]: (是否成功, 消息)
    """
    manager = ResetManager()
    return manager.reset(force)


def get_reset_preview() -> Dict[str, Any]:
    """
    获取重置预览信息
    
    Returns:
        Dict: 预览信息
    """
    manager = ResetManager()
    return manager.get_reset_preview()
