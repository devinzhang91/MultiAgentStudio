"""
MushTech TUI Studio - 纯键盘极客风格终端应用
用于管理 MushTech 员工代理并与 Gateway 通信
"""

from .app import MushTechStudioApp, main
from .models import Employee, EmployeeStore, MushTechConfig
from .client import MushTechClient
from .message_manager import MessageManager, Message, Conversation, get_message_manager
from .logger import logger, setup_logger

__all__ = [
    "MushTechStudioApp",
    "main",
    "Employee",
    "EmployeeStore", 
    "MushTechConfig",
    "MushTechClient",
    "MessageManager",
    "Message",
    "Conversation",
    "get_message_manager",
    "logger",
    "setup_logger",
]
__version__ = "0.3.0"
