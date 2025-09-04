#!/usr/bin/env python3
"""
WQB Expression Validator 数据管理工具
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .utils.fetch_data import login, get_operators, get_data_fields, get_all_data_fields
from .utils.logger import print_log


class DataManager:
    """数据管理器"""

    def __init__(self):
        self.config = self._load_config()
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        # 尝试加载 .env 文件
        env_file = Path.home() / ".wqb_validator" / ".env"
        if env_file.exists():
            load_dotenv(env_file)

            # 尝试加载当前目录的 .env 文件（开发环境优先）
        current_env = Path.cwd() / ".env"
        if current_env.exists():
            load_dotenv(current_env)
            print(f"📁 已加载开发环境配置: {current_env}")

        config = {
            "email": os.getenv("WQ_USERNAME"),
            "password": os.getenv("WQ_PASSWORD"),
            "base_url": os.getenv("WQ_BASE_URL", "https://api.worldquantbrain.com"),
        }

        return config

    def setup_credentials(
        self, email: str, password: str, base_url: Optional[str] = None
    ):
        """设置认证信息"""
        config_dir = Path.home() / ".wqb_validator"
        config_dir.mkdir(exist_ok=True)

        env_file = config_dir / ".env"
        env_content = f"""# WorldQuant BRAIN 平台配置
WQ_USERNAME={email}
WQ_PASSWORD={password}
WQ_BASE_URL={base_url or self.config['base_url']}
"""

        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)

        print(f"✅ 认证信息已保存到: {env_file}")
        print("🔒 请确保该文件的安全性，不要提交到版本控制系统")

        # 重新加载配置
        self.config = self._load_config()

    def check_credentials(self) -> bool:
        """检查认证信息是否完整"""
        if not self.config["email"] or not self.config["password"]:
            print("❌ 认证信息不完整")
            print("请使用以下命令设置认证信息:")
            print("  wqb-data setup <email> <password>")
            return False
        return True

    def authenticate(self) -> bool:
        """认证用户"""
        if not self.check_credentials():
            return False

        try:
            print("🔐 正在认证...")
            # 设置环境变量供fetch_data使用
            os.environ["WQ_USERNAME"] = self.config["email"]
            os.environ["WQ_PASSWORD"] = self.config["password"]

            # 尝试登录
            session = login()
            if session:
                print("✅ 认证成功！")
                return True
            else:
                print("❌ 认证失败")
                return False
        except Exception as e:
            print(f"❌ 认证失败: {e}")
            return False

    def fetch_all_data(self, force_update: bool = False):
        """获取所有数据"""
        if not self.authenticate():
            return False

        try:
            print("📥 正在获取操作符数据...")
            operators = get_operators()

            if operators is not None:
                # 保存操作符数据
                operators_file = self.data_dir / "operators.csv"
                operators.to_csv(operators_file, index=False)
                print(f"✅ 操作符数据已保存: {operators_file}")
            else:
                print("⚠️  操作符数据获取失败")

            print("📥 正在获取数据字段信息...")
            # 获取所有数据字段
            success_count, failed_count = get_all_data_fields()

            if success_count > 0:
                # 处理数据字段文件
                from .utils.handle_data import handle_data_fields

                handle_data_fields(str(self.data_dir))
                print(f"✅ 数据字段信息已处理: {self.data_dir}/data_fields.json")
            else:
                print("⚠️  数据字段信息获取失败")

            # 复制包内的valid_ops.json到用户数据目录
            package_valid_ops = Path(__file__).parent / "valid_ops.json"
            if package_valid_ops.exists():
                user_valid_ops = self.data_dir / "valid_ops.json"
                import shutil

                shutil.copy2(package_valid_ops, user_valid_ops)
                print(f"✅ 操作符定义文件已复制: {user_valid_ops}")

            print("🎉 数据获取完成！")
            return True

        except Exception as e:
            print(f"❌ 数据获取失败: {e}")
            return False

    def update_data(self):
        """更新数据"""
        print("🔄 开始更新数据...")

        # 检查数据文件是否存在
        operators_file = self.data_dir / "operators.csv"
        data_fields_file = self.data_dir / "data_fields.json"

        if not operators_file.exists() or not data_fields_file.exists():
            print("📥 数据文件不存在，开始首次获取...")
            return self.fetch_all_data()

        # 直接更新数据，不检查时间
        print("📥 数据文件存在，开始更新...")
        return self.fetch_all_data(force_update=True)

    def show_status(self):
        """显示数据状态"""
        print("📊 数据状态:")

        # 检查认证信息
        if self.check_credentials():
            print(f"  🔐 认证信息: ✅ ({self.config['email']})")
        else:
            print("  🔐 认证信息: ❌")

        # 检查数据文件
        operators_file = self.data_dir / "operators.csv"
        data_fields_file = self.data_dir / "data_fields.json"

        if operators_file.exists():
            size = operators_file.stat().st_size / 1024
            print(f"  📊 操作符数据: ✅ ({size:.1f} KB)")
        else:
            print("  📊 操作符数据: ❌")

        if data_fields_file.exists():
            size = data_fields_file.stat().st_size / 1024
            print(f"  📊 数据字段信息: ✅ ({size:.1f} KB)")
        else:
            print("  📊 数据字段信息: ❌")

        # 统计地区数据文件
        region_files = list(self.data_dir.glob("data_fields_*.json"))
        if region_files:
            print(f"  🌍 地区数据文件: ✅ ({len(region_files)} 个)")
        else:
            print("  🌍 地区数据文件: ❌")

        print("\n💡 提示: 使用 'wqb-data update' 手动更新数据")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="WQB Expression Validator 数据管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 设置认证信息
  wqb-data setup your.email@example.com your_password
  
  # 获取所有数据
  wqb-data fetch
  
  # 更新数据
  wqb-data update
  
  # 显示状态
  wqb-data status
  
  # 检查认证
  wqb-data auth
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # setup 命令
    setup_parser = subparsers.add_parser("setup", help="设置认证信息")
    setup_parser.add_argument("email", help="BRAIN 平台邮箱")
    setup_parser.add_argument("password", help="BRAIN 平台密码")
    setup_parser.add_argument("--base-url", help="API 基础URL")

    # fetch 命令
    fetch_parser = subparsers.add_parser("fetch", help="获取所有数据")
    fetch_parser.add_argument("--force", action="store_true", help="强制更新")

    # update 命令
    update_parser = subparsers.add_parser("update", help="更新数据")

    # status 命令
    status_parser = subparsers.add_parser("status", help="显示数据状态")

    # auth 命令
    auth_parser = subparsers.add_parser("auth", help="测试认证")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    data_manager = DataManager()

    if args.command == "setup":
        data_manager.setup_credentials(args.email, args.password, args.base_url)

    elif args.command == "fetch":
        data_manager.fetch_all_data(args.force)

    elif args.command == "update":
        data_manager.update_data()

    elif args.command == "status":
        data_manager.show_status()

    elif args.command == "auth":
        if data_manager.authenticate():
            print("✅ 认证测试通过")
        else:
            print("❌ 认证测试失败")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
