"""
MushTech TUI Studio - 纯键盘极客风格终端应用
用于管理 MushTech 员工代理并与 Gateway 通信
"""

from .app import MushTechStudioApp, main
from .models import Employee, EmployeeStore, create_employee_from_agent_config
from .client import MushTechClient, MushTechConfig
from .message_manager import MessageManager, Message, Conversation, get_message_manager
from .logger import logger, setup_logger

__all__ = [
    "MushTechStudioApp",
    "main",
    "Employee",
    "EmployeeStore",
    "create_employee_from_agent_config",
    "MushTechClient",
    "MushTechConfig",
    "MessageManager",
    "Message",
    "Conversation",
    "get_message_manager",
    "logger",
    "setup_logger",
]
__version__ = "0.3.0"
