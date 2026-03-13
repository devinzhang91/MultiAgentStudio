"""
MushTech Studio 工作室模板

提供三种预配置的工作室模板：
- software_engineering: 超级软件工程工作室
- remotion_video: Remotion视频工作室  
- stock_analysis: 股票分析工作室
"""

from .base import (
    StudioTemplate,
    AgentConfig,
    get_template,
    list_templates,
)
from .software_engineering import SoftwareEngineeringTemplate
from .remotion_video import RemotionVideoTemplate
from .stock_analysis import StockAnalysisTemplate

__all__ = [
    "StudioTemplate",
    "AgentConfig",
    "get_template",
    "list_templates",
    "SoftwareEngineeringTemplate",
    "RemotionVideoTemplate",
    "StockAnalysisTemplate",
]
