# 使用示例

本目录包含了 WQB Expression Validator 的各种使用示例。

## 📁 示例文件

### 1. basic_usage.py - 基本使用示例
最简单的验证器使用方式，适合初学者。

```bash
python examples/basic_usage.py
```

**功能**：
- 创建验证器实例
- 验证预定义的表达式列表
- 显示验证结果

### 2. batch_validation.py - 批量验证示例
批量验证多个表达式，适合处理大量数据。

```bash
python examples/batch_validation.py
```

**功能**：
- 批量验证表达式
- 统计验证结果
- 保存结果到JSON文件
- 错误详情分析

### 3. web_api.py - Web API示例
使用Flask创建Web API服务，适合集成到Web应用中。

```bash
# 安装Flask依赖
pip install flask

# 运行Web服务
python examples/web_api.py
```

**功能**：
- RESTful API接口
- 单个表达式验证
- 批量表达式验证
- 数据状态查询
- 健康检查

## 🚀 运行示例

### 前置条件
1. 已安装 wqb-expression-validator 包
2. 已配置认证信息：`wqb-data setup <email> <password>`
3. 已获取验证数据：`wqb-data fetch`

### 运行所有示例
```bash
# 基本使用
python examples/basic_usage.py

# 批量验证
python examples/batch_validation.py

# Web API（需要Flask）
python examples/web_api.py
```

## 🔧 自定义示例

您可以基于这些示例创建自己的验证脚本：

```python
from wqb_validator import ExpressionValidator

# 创建验证器
validator = ExpressionValidator()

# 验证您的表达式
result = validator.validate("ts_mean(close, 20)")

# 处理结果
if result.is_valid:
    print("✅ 表达式有效")
else:
    print("❌ 表达式无效:")
    for error in result.errors:
        print(f"  - {error.message}")
```

## 📚 更多信息

- 详细API文档：查看项目根目录的 README.md
- 数据管理：使用 `wqb-data` 命令管理验证数据
- 命令行验证：使用 `wqb-validate` 命令验证表达式
