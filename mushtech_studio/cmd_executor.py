"""
MushTech CMD 命令执行器
封装 mushtech agents 等命令，支持多智能体管理
"""

from __future__ import annotations

import json
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .logger import logger


@dataclass
class AgentInfo:
    """智能体信息"""
    id: str
    name: str
    workspace: str
    agent_dir: str
    model: str = ""
    is_default: bool = False
    bindings: List[Dict] = None
    
    def __post_init__(self):
        if self.bindings is None:
            self.bindings = []


class MushTechCmdExecutor:
    """执行 mushtech CLI 命令"""
    
    def __init__(self, binary: str = "openclaw"):
        self.binary = binary
        self._version: Optional[str] = None
        
    def _execute(
        self, 
        args: List[str], 
        timeout: int = 60,
    ) -> Tuple[bool, str]:
        """执行命令"""
        cmd = [self.binary] + args
        cmd_str = " ".join(cmd)
        logger.debug(f"[CMD] Executing: {cmd_str}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.debug(f"[CMD] Success: {cmd_str}")
                return True, result.stdout
            else:
                logger.warning(f"[CMD] Failed: {cmd_str}, stderr: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            logger.error(f"[CMD] Timeout: {cmd_str}")
            return False, f"命令超时（>{timeout}s）"
        except FileNotFoundError:
            logger.error(f"[CMD] Binary not found: {self.binary}")
            return False, f"未找到 {self.binary} 命令"
        except Exception as e:
            logger.exception(f"[CMD] Error executing: {cmd_str}")
            return False, str(e)
    
    def agents_list(self) -> List[AgentInfo]:
        """列出所有智能体"""
        args = ["agents", "list", "--json"]
        success, output = self._execute(args)
        agents = []
        
        if success and output.strip():
            try:
                data = json.loads(output)
                items = data if isinstance(data, list) else data.get("agents", [])
                
                for item in items:
                    agent = AgentInfo(
                        id=item.get("id", ""),
                        name=item.get("name", item.get("id", "")),
                        workspace=item.get("workspace", ""),
                        agent_dir=item.get("agentDir", ""),
                        model=item.get("model", ""),
                        is_default=item.get("default", False),
                        bindings=item.get("bindings", [])
                    )
                    agents.append(agent)
                    
            except json.JSONDecodeError as e:
                logger.error(f"[CMD] Failed to parse agents list: {e}")
                
        return agents
    
    def agents_add(
        self,
        name: str,
        workspace: Optional[str] = None,
        agent_dir: Optional[str] = None,
        model: Optional[str] = None,
        non_interactive: bool = True
    ) -> Tuple[bool, Dict]:
        """添加新智能体"""
        args = ["agents", "add", name, "--json"]
        
        if non_interactive:
            args.append("--non-interactive")
        if workspace:
            args.extend(["--workspace", workspace])
        if agent_dir:
            args.extend(["--agent-dir", agent_dir])
        if model:
            args.extend(["--model", model])
        
        success, output = self._execute(args, timeout=120)
        
        if success:
            try:
                result = json.loads(output) if output.strip() else {"success": True}
                logger.info(f"[CMD] Agent '{name}' added successfully")
                return True, result
            except json.JSONDecodeError:
                return True, {"output": output}
        else:
            logger.error(f"[CMD] Failed to add agent '{name}': {output}")
            return False, {"error": output}
    
    def agents_delete(self, agent_id: str, force: bool = False) -> Tuple[bool, str]:
        """删除智能体"""
        args = ["agents", "delete", agent_id]
        if force:
            args.append("--force")
            
        success, output = self._execute(args, timeout=60)
        
        if success:
            logger.info(f"[CMD] Agent '{agent_id}' deleted")
            return True, output or f"智能体 '{agent_id}' 已删除"
        else:
            logger.error(f"[CMD] Failed to delete agent '{agent_id}': {output}")
            return False, output
    
    def agents_set_identity(
        self,
        agent_id: str,
        name: Optional[str] = None,
        emoji: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """设置智能体身份信息"""
        args = ["agents", "set-identity", agent_id]
        
        if name:
            args.extend(["--name", name])
        if emoji:
            args.extend(["--emoji", emoji])
            
        success, output = self._execute(args)
        
        if success:
            logger.info(f"[CMD] Identity set for agent '{agent_id}'")
            return True, output or f"已更新 '{agent_id}' 的身份信息"
        else:
            return False, output


# 全局执行器实例
_cmd_executor: Optional[MushTechCmdExecutor] = None


def get_cmd_executor() -> MushTechCmdExecutor:
    """获取全局CMD执行器实例"""
    global _cmd_executor
    if _cmd_executor is None:
        _cmd_executor = MushTechCmdExecutor()
    return _cmd_executor
