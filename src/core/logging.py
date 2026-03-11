"""
日志配置模块
提供结构化日志记录，支持不同环境的日志级别和格式
"""

import logging
import sys
from typing import Optional


def setup_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """
    初始化日志配置

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: 运行环境
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # 根据环境选择日志格式
    if environment == "production":
        fmt = (
            '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"module":"%(name)s","message":"%(message)s"}'
        )
    else:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # 降低第三方库日志级别
    for noisy_logger in ("httpx", "httpcore", "neo4j", "urllib3", "asyncio"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取命名 Logger"""
    return logging.getLogger(name or "agent_system")
