"""
日志模块 - 记录应用运行情况
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class NoiseFilter(logging.Filter):
    """过滤高频噪声日志"""
    
    # 需要屏蔽的日志关键词
    NOISE_PATTERNS = [
        '"event":"tick"',           # WebSocket tick 事件
        '] WS recv:',                 # WebSocket 接收消息（匹配所有 emp-*）
        'Chat event, state=delta',    # 聊天增量事件
        '/__thinking__: thinking',    # 思考消息发送
        'Message received from emp-', # 思考消息接收（匹配所有 emp-*）
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for pattern in self.NOISE_PATTERNS:
            if pattern in message:
                return False  # 过滤掉匹配的消息
        return True  # 保留其他消息


def setup_logger(name: str = "mushtech", level: int = logging.DEBUG) -> logging.Logger:
    """设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 文件处理器 - 记录所有日志
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"mushtech_{datetime.now().strftime('%Y%m%d')}.log"
    # 创建噪声过滤器
    noise_filter = NoiseFilter()
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(noise_filter)  # 添加噪声过滤器
    logger.addHandler(file_handler)
    
    # 控制台处理器 - 只记录 WARNING 及以上（避免 INFO 干扰终端显示）
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(noise_filter)  # 添加噪声过滤器
    logger.addHandler(console_handler)
    
    return logger


# 全局日志记录器
logger = setup_logger()
