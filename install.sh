#!/bin/bash
# QuantMAx 一键安装脚本
# 用法: ./install.sh

set -e

echo "🚀 QuantMAx 一键安装开始..."

# 检查 Python 版本
if ! command -v python3.11 &> /dev/null; then
    echo "❌ 需要 Python 3.11+，请先安装"
    exit 1
fi

# 创建虚拟环境
echo "📦 创建虚拟环境..."
python3.11 -m venv .venv
source .venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install --upgrade pip -q
pip install -e . -q

# 下载数据
echo "📊 下载分钟线数据..."
quantopen download-1m

# 运行验证
echo "✅ 运行回测验证..."
quantopen backtest

echo ""
echo "🎉 安装完成！"
echo ""
echo "使用方法:"
echo "  source .venv/bin/activate"
echo "  quantopen --help"
