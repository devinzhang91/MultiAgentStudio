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
import time
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from .config_manager import get_config_manager
from .templates import get_template
from .logger import logger


class ResetManager:
    """重置管理器"""
    
    OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
    OPENCLAW_BACKUP_DIR = Path.home() / ".openclaw" / "backups"
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.studio_config = self.config_manager.get_config()
    
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
            
            # 8. 执行gateway restart
            success, message = self._restart_gateway()
            if not success:
                return False, f"重启Gateway失败: {message}"
            logger.info("[ResetManager] Gateway已重启")

            # 9. 向每位员工发送 /new，重建独立会话
            refreshed_count, failures = self._refresh_agent_sessions(template)
            logger.info(
                f"[ResetManager] 已向 {refreshed_count} 个会话发送 /new，失败 {len(failures)} 个"
            )

            summary = (
                f"重置完成！OpenClaw Gateway已重启，"
                f"并已向 {refreshed_count}/{len(template.get_agents())} 个员工会话发送 /new。"
            )
            if failures:
                summary += f" 失败会话: {'; '.join(failures)}"
            
            return True, summary
            
        except Exception as e:
            logger.exception("[ResetManager] 重置过程中发生错误")
            return False, f"重置失败: {str(e)}"
    
    def _clean_agents_config(self, agents_list: List[Dict]) -> List[Dict]:
        """
        清理agents配置，移除OpenClaw不识别的key
        
        Args:
            agents_list: 原始agents列表
            
        Returns:
            List[Dict]: 清理后的agents列表
        """
        cleaned = []
        for agent in agents_list:
            # 只保留OpenClaw识别的字段
            clean_agent = {
                "id": agent.get("id"),
                "name": agent.get("name"),
                "workspace": agent.get("workspace"),
                "agentDir": agent.get("agentDir"),
            }
            
            # 可选字段：identity
            if "identity" in agent:
                clean_agent["identity"] = agent["identity"]
            
            # 移除不被识别的字段：
            # - subagents (包含maxConcurrent, allowlist)
            # - agentToAgent
            
            cleaned.append(clean_agent)
        
        return cleaned
    
    def _backup_openclaw_config(self) -> Path:
        """
        备份openclaw.json
        
        Returns:
            Path: 备份文件路径
        """
        # 创建备份目录
        self.OPENCLAW_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"openclaw.json.bak.{timestamp}"
        backup_path = self.OPENCLAW_BACKUP_DIR / backup_filename
        
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
            
            # 获取新的agents配置
            base_workspace = self.studio_config.base_workspace
            architecture = self.studio_config.architecture
            new_agents_list = template.get_openclaw_agents_config(base_workspace, architecture)
            agent_ids = [a.id for a in template.get_agents()]
            
            # 更新agents.list（移除不被识别的key）
            config["agents"]["list"] = self._clean_agents_config(new_agents_list)

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

    def _get_hook_endpoint(self) -> Tuple[str, str]:
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

    def _post_agent_hook_message(self, endpoint: str, token: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
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

    def _refresh_agent_sessions(self, template) -> Tuple[int, List[str]]:
        """重启后向所有Agent会话发送 /new，确保上下文重置"""
        try:
            endpoint, token = self._get_hook_endpoint()
            refreshed_count = 0
            failures: List[str] = []

            for agent in template.get_agents():
                payload = {
                    "name": "MushTech Studio Reset",
                    "agentId": agent.id,
                    "sessionKey": f"agent:{agent.id}:main",
                    "message": "/new",
                }
                success, reason = self._post_agent_hook_message(endpoint, token, payload)
                if success:
                    refreshed_count += 1
                else:
                    failures.append(f"{agent.id}({reason})")

            return refreshed_count, failures
        except Exception as e:
            logger.error(f"[ResetManager] 发送 /new 失败: {e}")
            return 0, [str(e)]
    
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
