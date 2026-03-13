"""
配置管理器
管理MushTech Studio的全局配置
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


ARCHITECTURE_OPTIONS = [
    {
        "value": "centralized",
        "label": "主脑+专才模式（中心化调度）",
        "description": "唯一主脑负责接收需求、拆解任务、调用专才并统一汇总结果。适合流程严格、需要统一出口的团队。",
    },
    {
        "value": "decentralized",
        "label": "独立共享模式（去中心化协作）",
        "description": "每位成员可以独立协作，共享团队工作区与上下文。适合研究分析、并行讨论和信息共享。",
    },
    {
        "value": "hybrid",
        "label": "混合模式（生产级推荐）",
        "description": "主脑负责调度，专才共享团队工作区协作执行。兼顾统一编排与上下文共享，适合生产环境。",
    },
]

VALID_ARCHITECTURES = tuple(option["value"] for option in ARCHITECTURE_OPTIONS)
VALID_STUDIO_TYPES = (
    "software_engineering",
    "remotion_video",
    "stock_analysis",
)


def get_local_openclaw_token() -> str:
    """从本地 ~/.openclaw/openclaw.json 读取默认Gateway Token。

    连接Gateway鉴权优先使用 gateway.auth.token；若缺失，再回退 hooks.token。
    """
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return ""

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        gateway = data.get("gateway", {}) if isinstance(data, dict) else {}
        auth = gateway.get("auth", {}) if isinstance(gateway, dict) else {}
        gateway_token = str(auth.get("token") or "").strip()
        if gateway_token:
            return gateway_token

        hooks = data.get("hooks", {}) if isinstance(data, dict) else {}
        return str(hooks.get("token") or "").strip()
    except Exception:
        return ""


def get_default_workspace() -> str:
    """返回默认工作空间路径"""
    username = os.getenv("USER") or os.getenv("USERNAME") or "user"
    return f"/Users/{username}/MushTech-openclaw"


def get_architecture_options() -> list[dict[str, str]]:
    """返回架构选项定义"""
    return [option.copy() for option in ARCHITECTURE_OPTIONS]


@dataclass
class StudioConfig:
    """工作室全局配置"""
    
    # Gateway配置
    gateway_token: str = ""
    gateway_host: str = "127.0.0.1"
    gateway_port: int = 18789
    
    # 工作空间配置
    base_workspace: str = ""
    
    # 架构配置: centralized | decentralized | hybrid
    architecture: str = "hybrid"
    
    # 工作室类型: software_engineering | remotion_video | stock_analysis
    studio_type: str = "software_engineering"
    
    def __post_init__(self):
        """初始化后处理"""
        # 设置默认workspace路径
        if not self.base_workspace:
            self.base_workspace = get_default_workspace()

        # Token 为空时，从本地 openclaw.json 自动读取（优先 hooks.token）
        if not self.gateway_token:
            self.gateway_token = get_local_openclaw_token()
    
    @property
    def gateway_url(self) -> str:
        """生成Gateway URL"""
        return f"http://{self.gateway_host}:{self.gateway_port}"
    
    @property
    def gateway_ws_url(self) -> str:
        """生成Gateway WebSocket URL"""
        return f"ws://{self.gateway_host}:{self.gateway_port}"
    
    def get_architecture_display_name(self) -> str:
        """获取架构显示名称"""
        for option in ARCHITECTURE_OPTIONS:
            if option["value"] == self.architecture:
                return option["label"]
        return "未知"
    
    def get_studio_type_display_name(self) -> str:
        """获取工作室类型显示名称"""
        from .templates import list_templates
        
        templates = {t["id"]: t["name"] for t in list_templates()}
        return templates.get(self.studio_type, "未知")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudioConfig":
        """从字典创建"""
        valid_fields = {k for k in cls.__dataclass_fields__.keys()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


class ConfigManager:
    """配置管理器"""
    
    CONFIG_FILENAME = "studio_config.json"
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.config_file = self.data_dir / self.CONFIG_FILENAME
        self.data_dir.mkdir(exist_ok=True)
        
        self.config = StudioConfig()
        self.load()
    
    def load(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding='utf-8'))
                self.config = StudioConfig.from_dict(data)
            except Exception as e:
                print(f"[ConfigManager] 加载配置失败: {e}")
                self.config = StudioConfig()
    
    def save(self):
        """保存配置"""
        try:
            self.config_file.write_text(
                json.dumps(self.config.to_dict(), indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            return True
        except Exception as e:
            print(f"[ConfigManager] 保存配置失败: {e}")
            return False
    
    def get_config(self) -> StudioConfig:
        """获取当前配置"""
        return self.config
    
    def update_config(self, **kwargs) -> bool:
        """
        更新配置
        
        Args:
            **kwargs: 要更新的配置项
            
        Returns:
            bool: 是否成功
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        return self.save()
    
    def update_gateway_config(self, token: Optional[str] = None, 
                              host: Optional[str] = None, 
                              port: Optional[int] = None) -> bool:
        """
        更新Gateway配置
        
        Args:
            token: Gateway token
            host: Gateway主机地址
            port: Gateway端口
            
        Returns:
            bool: 是否成功
        """
        if token is not None:
            self.config.gateway_token = token
        if host is not None:
            self.config.gateway_host = host
        if port is not None:
            self.config.gateway_port = port
        
        return self.save()
    
    def update_workspace(self, base_workspace: str) -> bool:
        """
        更新工作空间路径
        
        Args:
            base_workspace: 基础工作空间路径
            
        Returns:
            bool: 是否成功
        """
        self.config.base_workspace = base_workspace
        return self.save()
    
    def update_architecture(self, architecture: str) -> bool:
        """
        更新架构配置
        
        Args:
            architecture: 架构类型 (centralized | decentralized | hybrid)
            
        Returns:
            bool: 是否成功
        """
        if architecture not in VALID_ARCHITECTURES:
            print(f"[ConfigManager] 无效架构: {architecture}")
            return False
        
        self.config.architecture = architecture
        return self.save()
    
    def update_studio_type(self, studio_type: str) -> bool:
        """
        更新工作室类型
        
        Args:
            studio_type: 工作室类型
            
        Returns:
            bool: 是否成功
        """
        if studio_type not in VALID_STUDIO_TYPES:
            print(f"[ConfigManager] 无效工作室类型: {studio_type}")
            return False
        
        self.config.studio_type = studio_type
        return self.save()
    
    def get_architecture_display_name(self) -> str:
        """获取架构显示名称"""
        return self.config.get_architecture_display_name()
    
    def get_studio_type_display_name(self) -> str:
        """获取工作室类型显示名称"""
        from .templates import list_templates
        
        templates = {t["id"]: t["name"] for t in list_templates()}
        return templates.get(self.config.studio_type, "未知")
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        验证配置有效性
        
        Returns:
            tuple: (是否有效, 错误信息列表)
        """
        errors = []
        
        # Token允许为空：为空时运行时会回退读取本地openclaw.json（优先hooks.token）

        if not self.config.gateway_host:
            errors.append("Gateway IP地址不能为空")
        
        if not (1 <= self.config.gateway_port <= 65535):
            errors.append("Gateway端口必须在1-65535之间")
        
        # 验证架构
        if self.config.architecture not in VALID_ARCHITECTURES:
            errors.append(f"无效架构: {self.config.architecture}")
        
        # 验证工作室类型
        if self.config.studio_type not in VALID_STUDIO_TYPES:
            errors.append(f"无效工作室类型: {self.config.studio_type}")
        
        # 验证workspace
        if not self.config.base_workspace:
            errors.append("Workspace路径不能为空")
        
        return len(errors) == 0, errors


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_studio_config() -> StudioConfig:
    """获取当前工作室配置"""
    return get_config_manager().get_config()
