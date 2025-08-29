#!/usr/bin/env python3
"""
WQB API 连接测试脚本
用于调试认证和API连接问题
"""

import os
import requests
import json
from dotenv import load_dotenv


def test_api_connection():
    """测试API连接"""
    print("🔍 测试WQB API连接...")

    # 加载环境变量
    load_dotenv(".env")

    username = os.getenv("WQ_USERNAME")
    password = os.getenv("WQ_PASSWORD")
    base_url = os.getenv("WQ_BASE_URL", "https://api.worldquantbrain.com")

    print(f"📋 配置信息:")
    print(f"  Base URL: {base_url}")
    print(f"  Username: {username}")
    print(f"  Password: {'*' * len(password) if password else 'None'}")

    if not username or not password:
        print("❌ 用户名或密码未设置")
        return False

    # 测试不同的认证端点
    auth_endpoints = [
        "/authentication",
        "/auth",
        "/login",
        "/api/v1/authentication",
        "/api/v1/auth",
        "/api/authentication",
        "/api/auth",
    ]

    session = requests.Session()
    session.auth = (username, password)

    print(f"\n🔐 测试认证端点...")

    for endpoint in auth_endpoints:
        url = f"{base_url}{endpoint}"
        print(f"  测试: {url}")

        try:
            response = session.post(url, timeout=10)
            print(f"    状态码: {response.status_code}")
            print(f"    响应头: {dict(response.headers)}")

            if response.status_code == 200 or response.status_code == 201:
                print(f"    ✅ 成功!")
                if response.text:
                    try:
                        data = response.json()
                        print(f"    响应数据: {json.dumps(data, indent=2)}")
                    except:
                        print(f"    响应文本: {response.text[:200]}...")
                return True
            elif response.status_code == 401:
                print(f"    ❌ 认证失败")
            elif response.status_code == 404:
                print(f"    ❌ 端点不存在")
            else:
                print(f"    ⚠️  其他错误")

        except requests.exceptions.RequestException as e:
            print(f"    ❌ 请求异常: {e}")

    print(f"\n🔍 测试其他API端点...")

    # 测试其他可能的端点
    test_endpoints = [
        "/operators",
        "/api/v1/operators",
        "/api/operators",
        "/data-fields",
        "/api/v1/data-fields",
        "/api/data-fields",
    ]

    for endpoint in test_endpoints:
        url = f"{base_url}{endpoint}"
        print(f"  测试: {url}")

        try:
            response = session.get(url, timeout=10)
            print(f"    状态码: {response.status_code}")

            if response.status_code == 200:
                print(f"    ✅ 端点可访问!")
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"    返回 {len(data)} 条记录")
                    elif isinstance(data, dict):
                        print(f"    返回字典，键: {list(data.keys())}")
                except:
                    print(f"    响应文本: {response.text[:100]}...")
            elif response.status_code == 401:
                print(f"    ❌ 需要认证")
            elif response.status_code == 404:
                print(f"    ❌ 端点不存在")
            else:
                print(f"    ⚠️  状态码: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"    ❌ 请求异常: {e}")

    return False


def test_environment():
    """测试环境变量"""
    print("🔍 测试环境变量...")

    # 检查.env文件
    if os.path.exists(".env"):
        print("✅ .env 文件存在")
        with open(".env", "r") as f:
            content = f.read()
            print(f"文件内容:\n{content}")
    else:
        print("❌ .env 文件不存在")

    # 检查环境变量
    print(f"\n环境变量:")
    print(f"  WQ_USERNAME: {os.getenv('WQ_USERNAME')}")
    print(
        f"  WQ_PASSWORD: {'*' * len(os.getenv('WQ_PASSWORD', '')) if os.getenv('WQ_PASSWORD') else 'None'}"
    )
    print(f"  WQ_BASE_URL: {os.getenv('WQ_BASE_URL')}")


if __name__ == "__main__":
    print("🚀 WQB API 连接测试")
    print("=" * 50)

    test_environment()
    print("\n" + "=" * 50)

    if test_api_connection():
        print("\n🎉 API连接测试成功!")
    else:
        print("\n❌ API连接测试失败")
        print("\n💡 建议:")
        print("1. 检查用户名和密码是否正确")
        print("2. 检查网络连接")
        print("3. 检查API端点是否正确")
        print("4. 联系WQB技术支持")
