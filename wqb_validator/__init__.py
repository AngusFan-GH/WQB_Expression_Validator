"""
WQB Expression Validator

A Python package for validating WorldQuant Brain (WQB) expressions.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# 主要导入
from .validator import ExpressionValidator
from .exceptions import ValidationError, ValidationResult
from .config import config, BASE_URL, DATA_DIR
from .data_manager import DataManager

# 版本信息
__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "ExpressionValidator",
    "ValidationError",
    "ValidationResult",
    "config",
    "BASE_URL",
    "DATA_DIR",
    "DataManager",
]


# 包级别信息
def get_version():
    """获取包版本"""
    return __version__


def get_author():
    """获取作者信息"""
    return __author__


def get_email():
    """获取邮箱信息"""
    return __email__
