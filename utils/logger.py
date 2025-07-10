from datetime import datetime


def get_timestamp():
    """获取当前时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def print_log(message, level="INFO", clear_line=False):
    """打印带时间戳的日志"""
    timestamp = get_timestamp()
    level_icon = {"INFO": "•", "WARNING": "!", "ERROR": "✗", "SUCCESS": "✓"}.get(
        level, "•"
    )

    if clear_line:
        # 清除当前行并打印新内容
        print(f"\r[{timestamp}] {level_icon} {message}", end="", flush=True)
    else:
        print(f"[{timestamp}] {level_icon} {message}")


def update_status(message, level="INFO"):
    """更新状态信息（覆盖当前行）"""
    timestamp = get_timestamp()
    level_icon = {"INFO": "•", "WARNING": "!", "ERROR": "✗", "SUCCESS": "✓"}.get(
        level, "•"
    )

    # 清除当前行并打印新内容
    print(f"\r[{timestamp}] {level_icon} {message}", end="", flush=True)


def update_bottom_status(message, level="INFO"):
    """更新底部状态信息（在进度条下方）"""
    timestamp = get_timestamp()
    level_icon = {"INFO": "•", "WARNING": "!", "ERROR": "✗", "SUCCESS": "✓"}.get(
        level, "•"
    )

    # 移动到进度条下方并更新状态
    print(f"\033[2K\r[{timestamp}] {level_icon} {message}", end="", flush=True)
