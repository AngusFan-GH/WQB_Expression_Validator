#!/usr/bin/env python3
"""
WQB Expression Validator 命令行接口
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional

from .validator import ExpressionValidator
from .exceptions import ValidationError, ValidationResult


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="Validate WorldQuant Brain (WQB) expressions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 验证单个表达式
  wqb-validate "ts_mean(close, 20)"

  # 验证表达式文件
  wqb-validate -f expression.txt

  # 指定配置
  wqb-validate -r USA -d 1 -u TOP3000 "ts_mean(close, 20)"

  # 输出JSON格式
  wqb-validate -j "ts_mean(close, 20)"

  # 详细输出
  wqb-validate -v "ts_mean(close, 20)"
        """,
    )

    parser.add_argument("expression", nargs="?", help="Expression to validate")

    parser.add_argument(
        "-f", "--file", type=str, help="File containing expression to validate"
    )

    parser.add_argument(
        "-r",
        "--region",
        default="USA",
        choices=["USA", "CHN", "EUR", "GLB", "ASI"],
        help="Market region (default: USA)",
    )

    parser.add_argument(
        "-d",
        "--delay",
        type=int,
        default=1,
        choices=[0, 1],
        help="Data delay in days (default: 1)",
    )

    parser.add_argument(
        "-u", "--universe", default="TOP3000", help="Stock universe (default: TOP3000)"
    )

    parser.add_argument(
        "-j", "--json", action="store_true", help="Output results in JSON format"
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    return parser


def validate_expression(
    expression: str,
    region: str = "USA",
    delay: int = 1,
    universe: str = "TOP3000",
    verbose: bool = False,
) -> ValidationResult:
    """验证表达式"""
    try:
        validator = ExpressionValidator(region, delay, universe)
        is_valid, errors = validator.validate(expression)

        # 转换为ValidationResult
        validation_errors = []
        for error_msg in errors:
            # 简单的错误解析（可以后续优化）
            validation_errors.append(ValidationError(message=error_msg))

        result = ValidationResult(
            is_valid=is_valid,
            errors=validation_errors,
            metadata={
                "region": region,
                "delay": delay,
                "universe": universe,
                "expression": expression,
            },
        )

        return result

    except Exception as e:
        # 创建错误结果
        error = ValidationError(message=f"验证器初始化失败: {str(e)}")
        return ValidationResult(
            is_valid=False,
            errors=[error],
            metadata={
                "region": region,
                "delay": delay,
                "universe": universe,
                "expression": expression,
            },
        )


def print_result(
    result: ValidationResult, json_output: bool = False, verbose: bool = False
):
    """打印验证结果"""
    if json_output:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    # 文本输出
    if result.is_valid:
        print("✅ 验证通过")
        if verbose and result.metadata:
            print(
                f"配置: {result.metadata['region']}_{result.metadata['delay']}_{result.metadata['universe']}"
            )
    else:
        print(f"❌ 验证失败 (发现 {result.error_count()} 个错误)")

        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. {error}")

        if verbose and result.metadata:
            print(
                f"\n配置: {result.metadata['region']}_{result.metadata['delay']}_{result.metadata['universe']}"
            )
            print(f"表达式: {result.metadata['expression']}")


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 检查是否有表达式输入
    if not args.expression and not args.file:
        parser.error("请提供表达式或使用 -f 指定文件")

    # 获取表达式
    expression = args.expression
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                expression = f.read().strip()
        except FileNotFoundError:
            print(f"❌ 文件不存在: {args.file}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            sys.exit(1)

    # 验证表达式
    result = validate_expression(
        expression=expression,
        region=args.region,
        delay=args.delay,
        universe=args.universe,
        verbose=args.verbose,
    )

    # 输出结果
    print_result(result, json_output=args.json, verbose=args.verbose)

    # 设置退出码
    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()
