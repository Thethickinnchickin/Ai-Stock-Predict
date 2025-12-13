import logging
import sys
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------
# Create a custom logger
# ---------------------------------------------------
log = logging.getLogger("AIStockBackend")
log.setLevel(logging.DEBUG)

# ---------------------------------------------------
# Formatting
# ---------------------------------------------------
console_format = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

file_format = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

# ---------------------------------------------------
# Console Handler (colored output optional)
# ---------------------------------------------------
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_format)
log.addHandler(console_handler)

# ---------------------------------------------------
# File Logging (optional: uncomment to enable)
# ---------------------------------------------------
# file_handler = RotatingFileHandler(
#     "logs/backend.log",
#     maxBytes=5_000_000,  # 5 MB
#     backupCount=3
# )
# file_handler.setLevel(logging.DEBUG)
# file_handler.setFormatter(file_format)
# log.addHandler(file_handler)

# ---------------------------------------------------
# Disable logging propagation
# ---------------------------------------------------
log.propagate = False


# ---------------------------------------------------
# Helper Functions
# ---------------------------------------------------
def info(msg: str):
    """Shorthand for log.info()"""
    log.info(msg)


def warn(msg: str):
    """Shorthand for log.warning()"""
    log.warning(msg)


def error(msg: str):
    """Shorthand for log.error()"""
    log.error(msg)


def debug(msg: str):
    """Shorthand for log.debug()"""
    log.debug(msg)
