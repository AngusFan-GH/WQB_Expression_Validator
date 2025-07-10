from utils.handle_data import handle_data_fields
from utils.logger import print_log
from utils.fetch_data import get_all_data_fields, get_operators
from validator.validator import validate_expression


if __name__ == "__main__":
    # print_log("=== 开始执行数据验证程序 ===", "INFO")

    # # 获取操作符数据
    # operators_df = get_operators()
    # if operators_df is not None:
    #     print_log(f"操作符数据获取完成，共 {len(operators_df)} 个操作符", "SUCCESS")
    # else:
    #     print_log("操作符数据获取失败", "ERROR")
    #     exit(1)

    # print_log("=" * 50, "INFO")

    # # 获取所有数据字段
    # success_count, failed_count = get_all_data_fields()

    # print_log("开始处理数据字段", "INFO")
    # handle_data_fields()
    # print_log("数据字段处理完成", "SUCCESS")

    test_expr = 'quantile(close, driver="cauchy")'
    ok, errs = validate_expression(test_expr, "USA", 1, "TOP500")

    print(f"表达式：{test_expr}")
    if ok:
        print("✅ 校验通过")
    else:
        print("❌ 校验失败:")
        for e in errs:
            print(" -", e)

    print_log("=" * 50, "INFO")
    print_log("=== 程序执行完成 ===", "SUCCESS")
