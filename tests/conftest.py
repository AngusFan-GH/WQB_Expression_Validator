"""
pytest配置文件
设置测试环境和共享fixture
"""

import sys
import os
import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def sample_validator():
    """创建示例验证器，供测试使用"""
    from validator.validator import ExpressionValidator

    return ExpressionValidator("USA", 1, "TOP3000")


@pytest.fixture(scope="session")
def sample_expressions():
    """示例表达式列表，供测试使用"""
    return [
        "ts_mean(close, 20)",
        "ts_rank(volume, 10)",
        "group_rank(close, sector)",
        "close * 2",
        "volume + open",
    ]


@pytest.fixture(scope="session")
def invalid_expressions():
    """无效表达式列表，供测试使用"""
    return [
        "ts_mean(close中文, 20)",  # 中文字符
        "ts_mean(close, 20",  # 缺少右括号
        "ts_mean(close, 20);",  # 多余分号
        "unknown_function(close)",  # 未知函数
        "ts_mean(invalid_field, 20)",  # 无效字段
    ]
