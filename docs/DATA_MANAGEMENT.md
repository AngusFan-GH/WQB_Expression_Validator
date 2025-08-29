# 数据管理指南

## 🔐 认证配置

### 1. 设置认证信息

首次使用前，需要设置您的 WorldQuant BRAIN 平台认证信息：

```bash
# 设置认证信息
wqb-data setup your.email@example.com your_password

# 可选：指定自定义API地址
wqb-data setup your.email@example.com your_password --base-url https://custom-api.example.com
```

认证信息将安全地保存在 `~/.wqb_validator/.env` 文件中。

### 2. 测试认证

设置完成后，可以测试认证是否成功：

```bash
wqb-data auth
```

## 📥 数据获取

### 1. 首次获取数据

```bash
# 获取所有数据（操作符、数据字段、各地区配置）
wqb-data fetch
```

这将获取：
- 操作符数据（operators.csv）
- 数据字段信息（data_fields.json）
- 各地区数据字段配置（data_fields_*.json）

### 2. 强制更新数据

```bash
# 强制更新所有数据
wqb-data fetch --force
```

## 🔄 数据更新

### 1. 手动更新数据

```bash
# 更新所有数据
wqb-data update
```

**注意**: 系统不会自动检测数据变化，需要用户主动更新。

### 2. 查看数据状态

```bash
# 查看当前数据状态
wqb-data status
```

显示：
- 认证信息状态
- 数据文件状态
- 文件大小和数量
- 更新配置信息

## ⚙️ 配置选项

### 环境变量配置

可以在 `.env` 文件中设置以下配置：

```bash
# 认证信息
WQ_EMAIL=your.email@example.com
WQ_PASSWORD=your_password

# API配置
WQ_BASE_URL=https://api.worldquantbrain.com

# 无自动更新配置，需要手动更新
```

### 配置文件位置

系统会按以下顺序查找配置文件：

1. `~/.wqb_validator/.env` （用户主目录）
2. `./.env` （当前工作目录）

**重要**: 系统不会自动检测数据变化，需要用户主动使用 `wqb-data update` 命令更新数据。

## 📁 数据文件结构

```
wqb_validator/data/
├── operators.csv                    # 操作符数据
├── data_fields.json                # 数据字段信息
├── data_fields_USA_0_TOP3000.json # 美国0延迟TOP3000数据字段
├── data_fields_USA_1_TOP3000.json # 美国1延迟TOP3000数据字段
├── data_fields_CHN_0_TOP2000U.json # 中国0延迟TOP2000U数据字段
├── data_fields_CHN_1_TOP2000U.json # 中国1延迟TOP2000U数据字段
├── data_fields_EUR_0_TOP1200.json  # 欧洲0延迟TOP1200数据字段
├── data_fields_EUR_1_TOP1200.json  # 欧洲1延迟TOP1200数据字段
└── ...                             # 其他地区配置
```

## 🔒 安全注意事项

1. **不要提交认证信息**：`.env` 文件包含敏感信息，不要提交到版本控制系统
2. **文件权限**：确保 `~/.wqb_validator/.env` 文件权限设置正确
3. **定期更新密码**：建议定期更新您的 BRAIN 平台密码

## 🚀 使用流程

### 完整使用流程

```bash
# 1. 安装包
pip install wqb-expression-validator

# 2. 设置认证信息
wqb-data setup your.email@example.com your_password

# 3. 测试认证
wqb-data auth

# 4. 获取数据
wqb-data fetch

# 5. 验证表达式
wqb-validate "ts_mean(close, 20)"

# 6. 定期更新数据
wqb-data update
```

### 手动更新建议

由于系统无法检测数据变化，建议：

1. **定期手动更新**: 根据您的使用频率，定期运行 `wqb-data update`
2. **重要更新后**: 当您知道有重要数据更新时，主动运行更新命令
3. **验证前检查**: 在验证重要表达式前，先运行 `wqb-data status` 检查数据状态

## 🐛 常见问题

### Q: 认证失败怎么办？
A: 检查邮箱和密码是否正确，确认网络连接正常

### Q: 数据获取失败？
A: 检查认证状态，确认API地址正确

### Q: 如何更改更新间隔？
A: 修改 `.env` 文件中的 `WQ_UPDATE_INTERVAL` 值

### Q: 数据文件损坏怎么办？
A: 使用 `wqb-data fetch --force` 强制重新获取

## 📞 技术支持

如果遇到问题，请：
1. 检查认证信息是否正确
2. 确认网络连接正常
3. 查看错误日志信息
4. 联系技术支持团队
