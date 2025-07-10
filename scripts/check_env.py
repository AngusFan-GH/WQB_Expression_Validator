#!/usr/bin/env python3
"""
检查环境变量设置
"""

import os
from dotenv import load_dotenv


def check_environment_variables():
    """
    检查WQB环境变量是否设置正确

    Returns:
        tuple: (是否设置正确: bool, 用户名: str, 密码: str)
    """
    # 加载环境变量
    load_dotenv()

    # 检查环境变量
    username = os.getenv("WQ_USERNAME")
    password = os.getenv("WQ_PASSWORD")

    is_valid = bool(username and password)

    return is_valid, username, password


def print_environment_status():
    """
    打印环境变量状态和设置提示
    """
    print("=== WQB 环境变量检查 ===")

    is_valid, username, password = check_environment_variables()

    print(f"用户名: {username if username else '❌ 未设置'}")
    print(f"密码: {'✅ 已设置' if password else '❌ 未设置'}")

    if not is_valid:
        print("\n❌ 环境变量未正确设置")
        print("\n请按照以下步骤设置：")
        print("1. 在项目根目录创建 .env 文件")
        print("2. 在 .env 文件中添加：")
        print("   WQ_USERNAME=your_actual_username")
        print("   WQ_PASSWORD=your_actual_password")
        print("3. 重新运行此脚本验证")
        return False

    print("\n✅ 环境变量设置正确")
    print("现在可以运行 python main.py")
    return True


def main():
    """主函数，用于独立运行脚本"""
    return print_environment_status()


if __name__ == "__main__":
    main()
