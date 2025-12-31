import logging
import sys

# ANSI颜色代码
REASONING = "\033[94m" # 蓝色
SUCCESS = "\033[92m"   # 绿色
WARNING = "\033[93m"   # 黄色
ERROR = "\033[91m"     # 红色
RESET = "\033[0m"      # 重置

def setup_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """
    配置并返回具有统一格式和颜色的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    class CustomFormatter(logging.Formatter):
        def format(self, record):
            msg = super().format(record)
            if record.levelno >= logging.ERROR:
                return f"{ERROR}{msg}{RESET}"
            elif record.levelno >= logging.WARNING:
                return f"{WARNING}{msg}{RESET}"
            # 逻辑日志（跟踪）
            return f"{REASONING}{msg}{RESET}"

    formatter = CustomFormatter('  ⚡ [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger
