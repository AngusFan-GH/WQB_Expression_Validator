#!/bin/bash

# 开发环境设置脚本
# 此脚本帮助开发者快速配置开发环境

echo "🔧 设置WQB Expression Validator开发环境..."

# 检查是否已存在.env文件
if [ -f ".env" ]; then
    echo "⚠️  .env文件已存在，跳过创建"
else
    echo "📝 创建开发环境配置文件..."
    
    # 创建.env文件
    cat > .env << 'EOF'
# WorldQuant BRAIN 平台开发环境配置
# 请修改下面的值为您的真实凭据

WQ_USERNAME=your_email@example.com
WQ_PASSWORD=your_password_here
WQ_BASE_URL=https://api.worldquantbrain.com
EOF
    
    echo "✅ .env文件已创建"
    echo "⚠️  请编辑 .env 文件，填入您的真实凭据"
fi

# 检查git配置
echo "🔍 检查git配置..."

if git config --get core.hooksPath > /dev/null 2>&1; then
    echo "✅ Git hooks已配置"
else
    echo "📝 设置Git hooks..."
    git config core.hooksPath .githooks
fi

# 检查是否已安装包
echo "🔍 检查包安装状态..."

if python -c "import wqb_validator" 2>/dev/null; then
    echo "✅ 包已安装"
else
    echo "📦 安装开发版本包..."
    pip install -e .
fi

echo ""
echo "🎉 开发环境设置完成！"
echo ""
echo "📋 下一步操作："
echo "1. 编辑 .env 文件，填入您的真实凭据"
echo "2. 运行 'wqb-data setup <email> <password>' 配置认证"
echo "3. 运行 'wqb-data fetch' 下载数据"
echo "4. 开始开发！"
echo ""
echo "⚠️  重要提醒："
echo "- .env 文件不会被提交到git"
echo "- 请确保凭据的安全性"
echo "- 不要将凭据分享给他人"
