import requests
import time
import random
from dotenv import load_dotenv
import os
import json
import pandas as pd
from tqdm import tqdm
from .logger import print_log


# 延迟加载环境变量，在需要时再加载
def _load_env_vars():
    """加载环境变量"""
    # 优先加载当前目录的.env文件（开发环境）
    current_env = os.path.join(os.getcwd(), ".env")
    if os.path.exists(current_env):
        load_dotenv(current_env)
        print(f"📁 已加载开发环境配置: {current_env}")
        return

    # 如果当前目录没有.env文件，则加载用户配置目录的.env文件
    user_env = os.path.expanduser("~/.wqb_validator/.env")
    if os.path.exists(user_env):
        load_dotenv(user_env)
        print(f"📁 已加载用户配置: {user_env}")


def _get_env_var(name, default=None):
    """获取环境变量，如果未设置则尝试加载"""
    value = os.getenv(name)
    if value is None:
        _load_env_vars()
        value = os.getenv(name, default)
    return value


# 延迟获取环境变量
def get_username():
    return _get_env_var("WQ_USERNAME")


def get_password():
    return _get_env_var("WQ_PASSWORD")


# 使用包的配置
from ..config import BASE_URL, DATA_DIR

# 配置已经通过导入获取

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

s = None


def make_request_with_retry(session, url, max_retries=3, base_delay=1, max_delay=10):
    """
    带重试机制的请求函数

    Args:
        session: requests会话
        url: 请求URL
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）

    Returns:
        response: 请求响应
    """
    for attempt in range(max_retries + 1):
        try:
            # 添加随机延迟，避免同时请求
            if attempt > 0:
                delay = min(base_delay * (2**attempt) + random.uniform(0, 1), max_delay)
                print_log(f"第 {attempt} 次重试，等待 {delay:.2f} 秒...", "WARNING")
                time.sleep(delay)

            response = session.get(url, timeout=30)

            # 检查是否被限流
            if response.status_code == 429:  # Too Many Requests
                retry_after = int(
                    response.headers.get("Retry-After", base_delay * (2**attempt))
                )
                print_log(f"请求被限流，等待 {retry_after} 秒后重试...", "WARNING")
                time.sleep(retry_after)
                continue

            # 检查其他错误状态码
            if response.status_code >= 500:  # 服务器错误
                if attempt < max_retries:
                    print_log(
                        f"服务器错误 {response.status_code}，准备重试...", "WARNING"
                    )
                    continue
                else:
                    print_log(
                        f"服务器错误 {response.status_code}，已达到最大重试次数",
                        "ERROR",
                    )
                    return response

            return response

        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                print_log(f"请求异常: {e}，准备重试...", "WARNING")
                continue
            else:
                print_log(f"请求失败: {e}，已达到最大重试次数", "ERROR")
                raise

    return None


def _show_environment_help():
    """显示环境变量设置帮助信息"""
    print_log("=" * 60, "WARNING")
    print_log("🔧 环境变量设置问题", "WARNING")
    print_log("=" * 60, "WARNING")

    # 检查环境变量状态
    username = os.getenv("WQ_USERNAME")
    password = os.getenv("WQ_PASSWORD")

    print_log(f"当前状态:", "INFO")
    print_log(f"  WQ_USERNAME: {'✅ 已设置' if username else '❌ 未设置'}", "INFO")
    print_log(f"  WQ_PASSWORD: {'✅ 已设置' if password else '❌ 未设置'}", "INFO")

    if not username or not password:
        print_log("", "INFO")
        print_log("📝 解决方案:", "INFO")
        print_log("1. 在项目根目录创建 .env 文件", "INFO")
        print_log("2. 在 .env 文件中添加以下内容:", "INFO")
        print_log("   WQ_USERNAME=your_actual_username", "INFO")
        print_log("   WQ_PASSWORD=your_actual_password", "INFO")
        print_log("3. 重新运行程序", "INFO")
        print_log("", "INFO")
        print_log("💡 提示: 运行 'python check_env.py' 检查环境变量", "INFO")
    else:
        print_log("", "INFO")
        print_log("⚠️  用户名或密码可能不正确", "WARNING")
        print_log("请检查 .env 文件中的凭据是否正确", "INFO")
        print_log("确保您的WQB账户有效且网络连接正常", "INFO")

    print_log("=" * 60, "WARNING")


def login():
    global s
    if s is not None:
        return s

    username = get_username()
    password = get_password()

    if not username or not password:
        _show_environment_help()
        return None

    print_log("开始登录认证...")
    s = requests.Session()
    s.auth = (username, password)

    start_time = time.time()
    response = s.post(f"{BASE_URL}/authentication")
    login_time = time.time() - start_time

    if response.status_code == 201:
        print_log(f"登录成功，耗时: {login_time:.2f}秒")
        return s
    else:
        print_log(f"登录失败，状态码: {response.status_code}", "ERROR")
        if response.status_code == 401:
            _show_environment_help()
        s = None
        return None


def get_operators():
    print_log("开始获取操作符数据...")

    if os.path.exists(f"{DATA_DIR}/operators.csv"):
        print_log("从本地缓存读取操作符数据")
        operators_df = pd.read_csv(f"{DATA_DIR}/operators.csv")
        print_log(f"成功读取 {len(operators_df)} 个操作符")
    else:
        print_log("从API获取操作符数据...")
        s = login()

        if s is None:
            print_log("登录失败，无法获取操作符数据", "ERROR")
            return None

        start_time = time.time()
        response = s.get(f"{BASE_URL}/operators")
        api_time = time.time() - start_time

        if response.status_code == 200:
            operators = response.json()
            operators_df = pd.DataFrame(operators)
            operators_df.to_csv(f"{DATA_DIR}/operators.csv", index=False)
            print_log(
                f"成功获取并保存 {len(operators_df)} 个操作符，API耗时: {api_time:.2f}秒"
            )
        else:
            print_log(f"获取操作符失败，状态码: {response.status_code}", "ERROR")
            return None

    return operators_df


def get_data_fields(region, delay, universe, request_delay=0.5):
    """
    获取数据字段

    Args:
        region: 地区
        delay: 延迟
        universe: 宇宙
        request_delay: 请求间隔时间（秒）
    """
    file_path = f"{DATA_DIR}/data_fields_{region}_{delay}_{universe}.json"

    # 检查本地缓存
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError:
            print_log(f"缓存文件损坏，将重新获取: {file_path}", "WARNING")
            os.remove(file_path)

    # 从API获取数据
    s = login()

    if s is None:
        print_log(f"登录失败，无法获取数据字段 - {region}_{delay}_{universe}", "ERROR")
        return None

    url = f"{BASE_URL}/data-fields?region={region}&delay={delay}&universe={universe}&instrumentType=EQUITY"

    # 添加请求间隔，避免同时请求过多
    if request_delay > 0:
        time.sleep(request_delay)

    start_time = time.time()
    response = make_request_with_retry(s, url)
    api_time = time.time() - start_time

    if response is None:
        print_log(f"请求失败 - {region}_{delay}_{universe}", "ERROR")
        return None

    # 检查响应状态码
    if response.status_code != 200:
        print_log(
            f"API请求失败 - {region}_{delay}_{universe}, 状态码: {response.status_code}",
            "ERROR",
        )
        print_log(f"响应内容: {response.text[:200]}...", "ERROR")
        return None

    # 检查响应内容
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print_log(f"JSON解析失败 - {region}_{delay}_{universe}", "ERROR")
        print_log(f"响应内容: {response.text[:200]}...", "ERROR")
        print_log(f"错误详情: {e}", "ERROR")
        return None

    # 保存到本地缓存
    try:
        with open(file_path, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print_log(f"保存缓存失败: {e}", "ERROR")

    return data


def get_settings():
    print_log("开始获取设置数据...")

    if os.path.exists(f"{DATA_DIR}/settings.json"):
        print_log("从本地缓存读取设置数据")
        with open(f"{DATA_DIR}/settings.json", "r") as f:
            settings = json.load(f)
    else:
        print_log("从API获取设置数据...")
        s = login()

        if s is None:
            print_log("登录失败，无法获取设置数据", "ERROR")
            return None

        response = s.options(f"{BASE_URL}/simulations").json()
        settings = response["actions"]["POST"]["settings"]["children"]
        with open(f"{DATA_DIR}/settings.json", "w") as f:
            json.dump(settings, f)
        print_log("设置数据已保存到缓存")

    return settings


def get_combinations(settings):
    regions = settings["region"]["choices"]["instrumentType"]["EQUITY"]
    delays = settings["delay"]["choices"]["instrumentType"]["EQUITY"]
    universes = settings["universe"]["choices"]["instrumentType"]["EQUITY"]
    combinations = []
    for region in regions:
        region_value = region["value"]
        region_delays = delays["region"].get(region_value, [])
        region_universes = universes["region"].get(region_value, [])

        for delay in region_delays:
            for universe in region_universes:
                combinations.append(
                    {
                        "region": region_value,
                        "delay": delay["value"],
                        "universe": universe["value"],
                    }
                )
    return combinations


def get_all_data_fields():
    print_log("开始获取所有数据字段...")

    settings = get_settings()
    if settings is None:
        print_log("无法获取设置数据，终止数据字段获取", "ERROR")
        return 0, 0

    all_combinations = get_combinations(settings)

    print_log(f"总共需要处理 {len(all_combinations)} 个组合")

    success_count = 0
    failed_count = 0
    consecutive_failures = 0  # 连续失败计数

    # 动态调整请求间隔
    base_delay = 0.5  # 基础间隔0.5秒
    current_delay = base_delay
    max_delay = 5.0  # 最大间隔5秒

    print_log("开始批量处理数据字段请求...")

    # 使用两个tqdm进度条：一个显示进度，一个显示状态
    with tqdm(
        all_combinations, desc="获取数据字段", unit="个组合", position=0, leave=True
    ) as pbar, tqdm(
        total=0, desc="", position=1, leave=True, bar_format="{desc}"
    ) as status_bar:
        for i, combo in enumerate(pbar):
            region = combo["region"]
            delay = combo["delay"]
            universe = combo["universe"]

            # 更新处理状态（在第二个进度条位置）
            pbar.set_description(f"正在处理 {region}_{delay}_{universe} ")

            # 根据连续失败情况调整请求间隔
            if consecutive_failures > 2:
                current_delay = min(current_delay * 1.5, max_delay)
                print_log(
                    f"连续失败 {consecutive_failures} 次，增加请求间隔到 {current_delay:.2f} 秒",
                    "WARNING",
                )

            data_fields = get_data_fields(
                region, delay, universe, request_delay=current_delay
            )

            if data_fields is not None:
                count = data_fields.get("count", "N/A")
                # 更新状态为成功信息
                status_bar.set_description(
                    f"✓ 成功获取 [{region}_{delay}_{universe}] 数据字段，数量 {count}"
                )
                success_count += 1
                consecutive_failures = 0  # 重置连续失败计数

                # 成功后逐渐减少请求间隔
                if consecutive_failures == 0 and current_delay > base_delay:
                    current_delay = max(current_delay * 0.9, base_delay)
            else:
                # 更新状态为失败信息
                status_bar.set_description(
                    f"✗ 获取 [{region}_{delay}_{universe}] 数据字段失败"
                )
                failed_count += 1
                consecutive_failures += 1

                # 如果连续失败过多，暂停一段时间
                if consecutive_failures >= 5:
                    pause_time = 10
                    print_log(
                        f"连续失败 {consecutive_failures} 次，暂停 {pause_time} 秒...",
                        "WARNING",
                    )
                    time.sleep(pause_time)
                    consecutive_failures = 0  # 重置计数

    print_log(
        f"数据字段获取完成！成功: {success_count}, 失败: {failed_count}", "SUCCESS"
    )
    return success_count, failed_count
