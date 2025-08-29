# WQB Expression Validator

这是一个用于验证 WorldQuant Brain (WQB) 表达式的 Python 包，采用模块化架构设计，提供严格的表达式验证功能。

## 🚀 快速开始

### 安装

```bash
# 从PyPI安装（发布后可用）
pip install wqb-expression-validator

**⚠️ 重要提示**: 安装后必须配置认证信息并下载数据才能使用！

# 从源码安装
git clone https://github.com/yourusername/wqb-expression-validator.git
cd wqb-expression-validator
pip install -e .
```

### 基本使用

**⚠️ 使用前必须配置认证信息并下载数据！**

```python
from wqb_validator import ExpressionValidator

# 创建验证器
validator = ExpressionValidator("USA", 1, "TOP3000")

# 验证表达式
result, errors = validator.validate("ts_mean(close, 20)")

if result:
    print("✅ 验证通过")
else:
    print(f"❌ 验证失败，发现 {len(errors)} 个错误")
    for error in errors:
        print(f"  - {error}")
```

### 命令行使用

```bash
# 验证单个表达式
wqb-validate "ts_mean(close, 20)"

# 验证表达式文件
wqb-validate -f expression.txt

# 指定配置
wqb-validate -r USA -d 1 -u TOP3000 "ts_mean(close, 20)"

# 输出JSON格式
wqb-validate -j "ts_mean(close, 20)"
```

## 🔐 数据管理

### 认证配置

首次使用前，需要配置您的 WorldQuant BRAIN 平台认证信息：

```bash
# 设置认证信息
wqb-data setup your.email@example.com your_password

# 测试认证
wqb-data auth
```

### 数据获取和更新

```bash
# 获取所有数据
wqb-data fetch

# 更新过期数据
wqb-data update

# 查看数据状态
wqb-data status
```

详细说明请参考 [数据管理指南](docs/DATA_MANAGEMENT.md)。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 环境配置

### 开发环境设置

我们提供了自动化的开发环境设置脚本：

```bash
# 运行开发环境设置脚本
./scripts/setup_dev_env.sh
```

这个脚本会：

- 创建 `.env` 开发配置文件
- 检查 git 配置
- 安装开发版本包
- 提供详细的后续操作指导

### 手动配置

如果您想手动配置，请按以下步骤操作：

#### 1. 创建开发配置文件

```bash
# 复制模板文件
cp .env.template .env

# 编辑配置文件
nano .env  # 或使用您喜欢的编辑器
```

#### 2. 配置 API 凭据

编辑 `.env` 文件，添加以下内容：

```env
# WQB API 凭据
# 请将下面的值替换为您的实际凭据
WQ_USERNAME=your_actual_username
WQ_PASSWORD=your_actual_password
WQ_BASE_URL=https://api.worldquantbrain.com
```

**⚠️ 重要安全提醒：**

- `.env` 文件包含敏感信息，不会被提交到 git
- 确保 `.env` 在 `.gitignore` 中
- 不要将凭据分享给他人
- 定期更新密码

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
validator = ExpressionValidator("USA", 1, "TOP3000")

# 验证表达式（只需传入表达式字符串）
ok, errors = validator.validate('ts_mean(close, 20)')

if ok:
    print("✅ 验证通过")
else:
    print("❌ 验证失败:")
    for error in errors:
        print(f"  - {error}")
```

#### 支持的验证功能

新架构提供以下验证功能：

1. **字符验证**：只允许 ASCII 字符，不允许中文字符、特殊符号等
2. **标识符验证**：变量名格式检查（不能数字开头、不能连续下划线）
3. **语法验证**：基于 Lark 语法的严格语法检查
4. **操作符验证**：基于 operators 数据的操作符存在性和参数验证
5. **数据字段验证**：基于 region/delay/universe 配置文件验证数据字段
6. **业务规则验证**：赋值语句规则、表达式结构等
7. **注释过滤**：自动过滤多行注释`/* ... */`和单行注释`# ...`

#### 高级功能

```python
# 获取验证器配置
print(f"配置: {validator.combination_key}")

# 获取有效字段列表
valid_fields = validator.get_valid_fields()
print(f"有效字段数量: {len(valid_fields)}")

# 验证多个表达式
expressions = ['ts_mean(volume, 20)', 'ts_rank(close, 30)', 'group_rank(close, sector)']
for expr in expressions:
    ok, errors = validator.validate(expr)
    print(f"{expr}: {'通过' if ok else '失败'}")

# 验证包含注释的表达式
expr_with_comments = '''
/* 这是一个多行注释 */
# 这是单行注释
ts_mean(close, 20)  # 计算20日移动平均
'''
ok, errors = validator.validate(expr_with_comments)
print(f"带注释表达式: {'通过' if ok else '失败'}")
```

## 项目结构

- `wqb_validator/` - 主包目录
  - `__init__.py` - 包初始化
  - `validator.py` - 核心验证器
  - `exceptions.py` - 异常定义
  - `config.py` - 配置管理
  - `cli.py` - 命令行接口
  - `data/` - 数据文件目录
  - `utils/` - 工具函数目录
  - `grammar.lark` - 语法定义
  - `valid_ops.json` - 操作符配置
- `tests/` - 测试目录
  - `test_all_cases.py` - 全面测试用例
  - `test_var_args.py` - 可变参数测试
  - `run_tests.py` - 测试运行脚本
  - `conftest.py` - pytest 配置文件
  - `README.md` - 测试说明文档
- `docs/` - 文档目录
- `pyproject.toml` - 项目配置
- `MANIFEST.in` - 文件清单
- `LICENSE` - 许可证
- `build_package.py` - 包构建脚本

## 注意事项

- 首次运行时会从 API 获取数据，需要有效的 WQB 账户
- 数据会缓存在 `data/` 目录中
- 确保网络连接正常以访问 WQB API
- 如果遇到 401 认证错误，请检查 `.env` 文件中的用户名和密码是否正确
- `.env` 文件包含敏感信息，请确保不要将其提交到版本控制系统
- 建议将 `.env` 添加到 `.gitignore` 文件中
