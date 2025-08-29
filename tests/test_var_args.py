#!/usr/bin/env python3
"""
测试可变参数函数的处理
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validator.validator import ExpressionValidator


def test_var_args():
    validator = ExpressionValidator("USA", 0, "TOP500")

    test_cases = [
        # multiply 函数测试 - 可变参数
        {
            "name": "multiply基本用法",
            "expr": "multiply(close, volume)",
            "should_fail": False,
        },
        {
            "name": "multiply三个参数",
            "expr": "multiply(close, volume, open)",
            "should_fail": False,
        },
        {
            "name": "multiply带命名参数",
            "expr": "multiply(close, volume, filter=false)",
            "should_fail": False,
        },
        {
            "name": "multiply混合参数",
            "expr": "multiply(close, volume, open, filter=true)",
            "should_fail": False,
        },
        {
            "name": "multiply参数不足",
            "expr": "multiply(close)",
            "should_fail": True,
        },
        {
            "name": "multiply参数类型错误",
            "expr": 'multiply(close, "volume")',
            "should_fail": True,
        },
        {
            "name": "multiply命名参数错误",
            "expr": "multiply(close, volume, invalid_param=true)",
            "should_fail": True,
        },
        # max 函数测试 - 可变参数
        {
            "name": "max基本用法",
            "expr": "max(close, volume)",
            "should_fail": False,
        },
        {
            "name": "max三个参数",
            "expr": "max(close, volume, open)",
            "should_fail": False,
        },
        {
            "name": "max参数不足",
            "expr": "max(close)",
            "should_fail": True,
        },
        # min 函数测试 - 可变参数
        {
            "name": "min基本用法",
            "expr": "min(close, volume)",
            "should_fail": False,
        },
        {
            "name": "min三个参数",
            "expr": "min(close, volume, open)",
            "should_fail": False,
        },
        {
            "name": "min参数不足",
            "expr": "min(close)",
            "should_fail": True,
        },
        # add 函数测试 - 固定参数
        {
            "name": "add基本用法",
            "expr": "add(close, volume)",
            "should_fail": False,
        },
        {
            "name": "add带命名参数",
            "expr": "add(close, volume, filter=false)",
            "should_fail": False,
        },
        {
            "name": "add参数不足",
            "expr": "add(close)",
            "should_fail": True,
        },
        {
            "name": "add参数过多",
            "expr": "add(close, volume, open)",
            "should_fail": True,
        },
        # 复杂嵌套测试
        {
            "name": "复杂嵌套multiply",
            "expr": "a = ts_mean(close, 20); b = multiply(a, volume, open); b * 2",
            "should_fail": False,
        },
        {
            "name": "复杂嵌套max",
            "expr": "a = ts_mean(close, 20); b = ts_mean(volume, 20); c = max(a, b, open); c * 2",
            "should_fail": False,
        },
        {
            "name": "变量作为可变参数",
            "expr": "a = ts_mean(close, 20); b = ts_mean(volume, 20); c = multiply(a, b); c * 2",
            "should_fail": False,
        },
    ]

    print("=== 可变参数函数测试 ===\n")
    for i, test_case in enumerate(test_cases, 1):
        print(f"测试 {i}: {test_case['name']}")
        print(f"表达式: {test_case['expr']}")
        is_valid, errors = validator.validate(test_case["expr"])
        if test_case["should_fail"]:
            if is_valid:
                print("❌ 应该失败但通过了")
            else:
                print("✅ 正确失败")
                for error in errors:
                    print(f"  {error}")
        else:
            if is_valid:
                print("✅ 正确通过")
            else:
                print("❌ 应该通过但失败了")
                for error in errors:
                    print(f"  {error}")
        print("-" * 50)


if __name__ == "__main__":
    test_var_args()
