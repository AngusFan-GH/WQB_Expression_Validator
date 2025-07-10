import json
from utils.handle_data import handle_data_fields
from utils.logger import print_log
from utils.fetch_data import DATA_DIR, get_all_data_fields, get_operators
from validator.validator import ExpressionValidator
import os


def handle_operators():
    if not os.path.exists(f"{DATA_DIR}/operators.csv"):
        operators_df = get_operators()
        if operators_df is not None:
            print_log(f"操作符数据获取完成，共 {len(operators_df)} 个操作符", "SUCCESS")
        else:
            print_log("操作符数据获取失败", "ERROR")
            exit(1)


def handle_data_fields():
    # 获取所有数据字段
    if not os.path.exists(f"{DATA_DIR}/data_fields.json"):
        success_count, failed_count = get_all_data_fields()
        if success_count == 0 and failed_count == 0:
            print_log("所有数据字段获取失败", "ERROR")
            exit(1)

        print_log("开始处理数据字段", "INFO")
        handle_data_fields()
        print_log("数据字段处理完成", "SUCCESS")


if __name__ == "__main__":
    print_log("=== 开始获取数据字段和操作符 ===", "INFO")

    handle_operators()

    handle_data_fields()

    print_log("=== 程序执行完成 ===", "SUCCESS")
