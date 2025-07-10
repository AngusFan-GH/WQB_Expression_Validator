# WQB Expression Validator

这是一个用于验证 WorldQuant Brain (WQB) 表达式的 Python 项目。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 环境配置

### 1. 创建 .env 文件

在项目根目录下创建 `.env` 文件：

```bash
# 方法1：使用命令行创建
touch .env

# 方法2：使用文本编辑器创建
# 在项目根目录下创建名为 .env 的文件
```

### 2. 配置 API 凭据

编辑 `.env` 文件，添加以下内容：

```env
# WQB API 凭据
# 请将下面的值替换为您的实际凭据
WQ_USERNAME=your_actual_username
WQ_PASSWORD=your_actual_password
```

**重要说明：**

- `your_actual_username` 替换为您的 WQB 用户名
- `your_actual_password` 替换为您的 WQB 密码
- 不要在用户名和密码周围添加引号
- 确保没有多余的空格

### 3. 验证环境变量

运行以下命令验证环境变量是否正确设置：

```bash
# 方法1：使用提供的检查脚本
python check_env.py

# 方法2：使用Python命令
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
username = os.getenv('WQ_USERNAME')
password = os.getenv('WQ_PASSWORD')
print('用户名:', username if username else '未设置')
print('密码:', '已设置' if password else '未设置')
"
```

### 4. 常见问题

**问题 1：状态码 401 错误**

- 程序会自动检测并显示环境变量设置帮助
- 检查用户名和密码是否正确
- 确认 WQB 账户是否有效
- 检查网络连接是否正常
- 运行 `python check_env.py` 验证环境变量设置

**问题 2：环境变量未加载**

- 确保 `.env` 文件在项目根目录
- 检查文件格式是否正确（UTF-8 编码）
- 确认没有多余的空格或特殊字符

**问题 3：权限问题**

- 确保 `.env` 文件有正确的读取权限
- 在 Windows 上，确保文件不是只读的

## 使用方法

### 运行主程序

```bash
python main.py
```

程序会自动：

1. 获取操作符数据
2. 获取数据字段信息
3. 处理数据字段
4. 验证示例表达式

### 智能错误提示

程序具有智能错误检测功能：

- **认证错误自动检测**：当遇到 401 认证错误时，程序会自动检查环境变量并显示详细的设置指导
- **环境变量验证**：运行 `python check_env.py` 可以快速验证环境变量设置
- **详细错误信息**：提供清晰的错误原因和解决方案

### 表达式验证器使用

#### 基本用法

```python
from validator.validator import ExpressionValidator

# 创建验证器（初始化时设置地区、延迟、股票池）
validator = ExpressionValidator("USA", 1, "TOP500")

# 验证表达式（只需传入表达式字符串）
ok, errors = validator.validate('quantile(close, driver="cauchy")')

if ok:
    print("✅ 验证通过")
else:
    print("❌ 验证失败:")
    for error in errors:
        print(f"  - {error}")
```

#### 高级功能

```python
# 获取验证器配置
config = validator.get_config()
print(f"配置: {config}")

# 获取有效字段列表
valid_fields = validator.get_valid_fields()
print(f"有效字段数量: {len(valid_fields)}")

# 验证多个表达式
expressions = ['mean(volume, 20)', 'std(returns, 30)']
for expr in expressions:
    ok, errors = validator.validate(expr)
    print(f"{expr}: {'通过' if ok else '失败'}")
```

## 项目结构

- `main.py` - 主程序入口
- `utils/` - 工具函数
  - `fetch_data.py` - 数据获取
  - `handle_data.py` - 数据处理
  - `logger.py` - 日志工具
- `validator/` - 验证器
  - `validator.py` - 表达式验证逻辑（包含 ExpressionValidator 类）
  - `grammar.lark` - 语法定义
  - `valid_ops.json` - 有效操作符配置
- `data/` - 数据目录（自动生成）
- `config.json` - 配置文件

## 注意事项

- 首次运行时会从 API 获取数据，需要有效的 WQB 账户
- 数据会缓存在 `data/` 目录中
- 确保网络连接正常以访问 WQB API
- 如果遇到 401 认证错误，请检查 `.env` 文件中的用户名和密码是否正确
- `.env` 文件包含敏感信息，请确保不要将其提交到版本控制系统
- 建议将 `.env` 添加到 `.gitignore` 文件中
