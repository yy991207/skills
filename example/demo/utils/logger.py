import logging
import sys

# ANSI Color Codes
REASONING = "\033[94m" # Blue
SUCCESS = "\033[92m"   # Green
WARNING = "\033[93m"   # Yellow
ERROR = "\033[91m"     # Red
RESET = "\033[0m"      # Reset

def setup_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger with consistent formatting and colors
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
            # Logic logs (trace)
            return f"{REASONING}{msg}{RESET}"

    formatter = CustomFormatter('  ⚡ [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger
