#!/usr/bin/env python3
"""
全面表达式校验测试用例
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wqb_validator.validator import ExpressionValidator


def test_all_cases():
    validator = ExpressionValidator("USA", 0, "TOP500")
    test_cases = [
        # 标识符规则
        {
            "name": "标识符以数字开头",
            "expr": "1price = close; close * 2；",
            "should_fail": True,
        },
        {
            "name": "标识符连续下划线",
            "expr": "price__data = close; close * 2",
            "should_fail": True,
        },
        {
            "name": "标识符正常",
            "expr": "price_data = close; price_data * 2",
            "should_fail": False,
        },
        # 数字格式
        {
            "name": "数字多个小数点",
            "expr": "price = 3.14.15; close * 2",
            "should_fail": True,
        },
        {"name": "数字正常", "expr": "price = 3.14; price * 2", "should_fail": False},
        # 字符串格式
        {
            "name": "字符串未闭合",
            "expr": 'price = "close; price * 2',
            "should_fail": True,
        },
        {
            "name": "字符串正常",
            "expr": 'price = "close"; price * 2',
            "should_fail": False,
        },
        # 操作符
        {
            "name": "连续操作符",
            "expr": "price = close ** 2; price * 2",
            "should_fail": True,
        },
        {
            "name": "连续操作符2",
            "expr": "price = close ++ 1; price * 2",
            "should_fail": True,
        },
        {
            "name": "操作符正常",
            "expr": "price = close + 1; price * 2",
            "should_fail": False,
        },
        # 括号
        {
            "name": "缺少右括号",
            "expr": "price = (close + volume; price * 2",
            "should_fail": True,
        },
        {
            "name": "缺少左括号",
            "expr": "price = close + volume); price * 2",
            "should_fail": True,
        },
        {
            "name": "括号正常",
            "expr": "price = (close + volume); price * 2",
            "should_fail": False,
        },
        # 逗号/分号
        {
            "name": "连续逗号",
            "expr": "ts_avg(close,, volume); close * 2",
            "should_fail": True,
        },
        {"name": "连续分号", "expr": "price = close;; volume * 2", "should_fail": True},
        {
            "name": "逗号分号正常",
            "expr": "ts_mean(close, 20); close * 2",
            "should_fail": False,
        },
        # 注释行
        {"name": "注释行", "expr": "# 这是注释\nclose * 2", "should_fail": False},
        {"name": "行内注释", "expr": "close * 2 # 收盘价乘2", "should_fail": False},
        {"name": "空行", "expr": "\n\nclose * 2\n", "should_fail": False},
        # 复杂嵌套
        {
            "name": "复杂嵌套表达式",
            "expr": "a = ts_mean(close, 20); b = ts_rank(a, 10); b * 2",
            "should_fail": False,
        },
        {
            "name": "复杂嵌套类型错误",
            "expr": 'a = ts_mean(close, 20); b = ts_rank(a, "10"); b * 2',
            "should_fail": True,
        },
        {
            "name": "未知操作符",
            "expr": "a = ts_avg(close, 20); b = ts_rank(a, 10); b * 2",
            "should_fail": True,
        },
        {
            "name": "未知字段",
            "expr": "a = ts_mean(unknown_field, 20); a * 2",
            "should_fail": True,
        },
        {
            "name": "数据字段不能作为变量",
            "expr": "close = 1; close * 2",
            "should_fail": True,
        },
        {"name": "多行注释", "expr": "/* 多行注释 */\nclose * 2", "should_fail": False},
        {
            "name": "括号位置错误",
            "expr": "a (= ts_mean(close, 20); b = ts_rank(a, 10); b * 2",
            "should_fail": True,
        },
        {
            "name": "括号位置错误2",
            "expr": "a = ts_mean((close), 20); b = ts_rank(a, 10); b * 2",
            "should_fail": False,
        },
        # Group操作符测试
        {
            "name": "group_mean正常",
            "expr": "a = group_mean(close, volume, sector); a * 2",
            "should_fail": False,
        },
        {
            "name": "group_mean参数不足",
            "expr": "a = group_mean(close, volume); a * 2",
            "should_fail": True,
        },
        {
            "name": "group_rank正常",
            "expr": "a = group_rank(close, sector); a * 2",
            "should_fail": False,
        },
        {
            "name": "group_rank参数过多",
            "expr": "a = group_rank(close, sector, volume); a * 2",
            "should_fail": True,
        },
        {
            "name": "group_extra正常",
            "expr": "a = group_extra(close, volume, industry); a * 2",
            "should_fail": False,
        },
        {
            "name": "group_backfill正常",
            "expr": "a = group_backfill(close, sector, 20); a * 2",
            "should_fail": False,
        },
        {
            "name": "group_backfill带命名参数",
            "expr": "a = group_backfill(close, sector, 20, std=3.0); a * 2",
            "should_fail": False,
        },
        {
            "name": "group_scale正常",
            "expr": "a = group_scale(close, country); a * 2",
            "should_fail": False,
        },
        {
            "name": "group_zscore正常",
            "expr": "a = group_zscore(close, sector); a * 2",
            "should_fail": False,
        },
        {
            "name": "group_neutralize正常",
            "expr": "a = group_neutralize(close, industry); a * 2",
            "should_fail": False,
        },
        {
            "name": "group_cartesian_product正常",
            "expr": "a = group_cartesian_product(sector, country); a * 2",
            "should_fail": False,
        },
        # 复杂嵌套测试
        {
            "name": "多层嵌套函数调用",
            "expr": "a = ts_mean(close, 20); b = group_rank(a, sector); c = ts_rank(b, 10); c * 2",
            "should_fail": False,
        },
        {
            "name": "混合操作符嵌套",
            "expr": "a = ts_mean(close, 20); b = group_scale(a, sector); c = ts_quantile(b, 10); d = group_neutralize(c, industry); d * 2",
            "should_fail": False,
        },
        {
            "name": "复杂表达式嵌套",
            "expr": "a = ts_mean(close, 20); b = group_rank(a, sector); c = ts_rank(b, 10); d = group_zscore(c, country); e = ts_delta(d, 5); e * 2",
            "should_fail": False,
        },
        {
            "name": "多变量复杂嵌套",
            "expr": "price_ma = ts_mean(close, 20); volume_ma = ts_mean(volume, 20); price_rank = group_rank(price_ma, sector); volume_rank = group_rank(volume_ma, sector); combined = price_rank * volume_rank; final = ts_rank(combined, 10); final * 2",
            "should_fail": False,
        },
        {
            "name": "嵌套表达式类型错误",
            "expr": 'a = ts_mean(close, 20); b = group_rank(a, "sector"); c = ts_rank(b, 10); c * 2',
            "should_fail": True,
        },
        {
            "name": "复杂嵌套未知操作符",
            "expr": "a = ts_mean(close, 20); b = group_avg(a, sector); c = ts_rank(b, 10); c * 2",
            "should_fail": True,
        },
        {
            "name": "复杂嵌套未知字段",
            "expr": "a = ts_mean(close, 20); b = group_rank(a, unknown_field); c = ts_rank(b, 10); c * 2",
            "should_fail": True,
        },
        {
            "name": "多行复杂嵌套",
            "expr": "price_ma = ts_mean(close, 20);\nvolume_ma = ts_mean(volume, 20);\nprice_rank = group_rank(price_ma, sector);\nvolume_rank = group_rank(volume_ma, sector);\ncombined = price_rank * volume_rank;\nfinal = ts_rank(combined, 10);\nfinal * 2",
            "should_fail": False,
        },
        {
            "name": "复杂嵌套带注释",
            "expr": "# 计算价格移动平均\nprice_ma = ts_mean(close, 20);\n# 计算成交量移动平均\nvolume_ma = ts_mean(volume, 20);\n# 分组排名\nprice_rank = group_rank(price_ma, sector);\nvolume_rank = group_rank(volume_ma, sector);\n# 组合信号\ncombined = price_rank * volume_rank;\n# 最终排名\nfinal = ts_rank(combined, 10);\nfinal * 2",
            "should_fail": False,
        },
        # 调试测试
        {
            "name": "调试变量类型推断",
            "expr": "a = ts_mean(close, 20); b = group_rank(a, sector); c = b * 2; c",
            "should_fail": False,
        },
        # 简单多行测试
        {
            "name": "简单多行测试",
            "expr": "a = ts_mean(close, 20);\nb = group_rank(a, sector);\nc = b * 2;\nc",
            "should_fail": False,
        },
        # 详细调试测试
        {
            "name": "详细调试测试",
            "expr": "price_ma = ts_mean(close, 20);\nvolume_ma = ts_mean(volume, 20);\nprice_rank = group_rank(price_ma, sector);\nvolume_rank = group_rank(volume_ma, sector);\ncombined = price_rank * volume_rank;\nfinal = ts_rank(combined, 10);\nfinal * 2",
            "should_fail": False,
        },
        # 简单算术运算测试
        {
            "name": "简单算术运算测试",
            "expr": "a = ts_mean(close, 20); b = group_rank(a, sector); c = b * 2; ts_rank(c, 10)",
            "should_fail": False,
        },
        # 逐步调试测试
        {
            "name": "逐步调试测试1",
            "expr": "a = ts_mean(close, 20); a",
            "should_fail": False,
        },
        {
            "name": "逐步调试测试2",
            "expr": "a = ts_mean(close, 20); b = group_rank(a, sector); b",
            "should_fail": False,
        },
        {
            "name": "逐步调试测试3",
            "expr": "a = ts_mean(close, 20); b = group_rank(a, sector); c = b * 2; c",
            "should_fail": False,
        },
        # 函数参数类型检查测试
        {
            "name": "函数参数类型检查测试1",
            "expr": "a = ts_mean(close, 20); ts_rank(a, 10)",
            "should_fail": False,
        },
        {
            "name": "函数参数类型检查测试2",
            "expr": "a = ts_mean(close, 20); b = group_rank(a, sector); ts_rank(b, 10)",
            "should_fail": False,
        },
        {
            "name": "函数参数类型检查测试3",
            "expr": "a = ts_mean(close, 20); b = group_rank(a, sector); c = b * 2; ts_rank(c, 10)",
            "should_fail": False,
        },
        {
            "name": "可变参数类型检查",
            "expr": "multiply(close ,volume,volume,volume , filter=false)",
            "should_fail": False,
        },
        {
            "name": "可变参数类型检查2",
            "expr": "min(close ,volume , close, volume)",
            "should_fail": False,
        },
        {
            "name": "可变参数类型检查3",
            "expr": "max(close ,volume , close, volume, close, volume)",
            "should_fail": False,
        },
        {
            "name": "if-else表达式",
            "expr": "if(rank(close) > 0.1, volume, ts_rank(close, 10))",
            "should_fail": True,
        },
        {
            "name": "if-else表达式2",
            "expr": "c=rank(close) > 0.1;if_else(c, volume, ts_rank(close, 10))",
            "should_fail": False,
        },
        {
            "name": "if-else表达式3",
            "expr": "c=rank(close) > 0.1;a=ts_rank(close, 10);if_else(c, volume, a)",
            "should_fail": False,
        },
        {
            "name": "if-else直接比较表达式",
            "expr": "if_else(rank(close) > 0.1, volume, ts_rank(close, 10))",
            "should_fail": False,
        },
        {
            "name": "ts_regression",
            "expr": "ts_regression(volume , close, 10, lag=0, rettype=0)",
            "should_fail": False,
        },
    ]
    print("=== 全面表达式校验测试 ===\n")
    for i, test_case in enumerate(test_cases, 1):
        print(f"测试 {i}: {test_case['name']}")
        print(f"表达式:\n{test_case['expr']}")
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
    test_all_cases()
