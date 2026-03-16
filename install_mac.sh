#!/bin/bash
# ============================================================
# 幕布AI分析工具 - Mac 一键安装脚本
# 运行方式：在终端中执行 bash install_mac.sh
# ============================================================

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          幕布知识库 AI 分析工具 - 安装程序               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 检查 Python3 是否已安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 未检测到 Python3，请先安装 Python3："
    echo "   访问 https://www.python.org/downloads/ 下载安装"
    echo "   或使用 Homebrew：brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "✅ 检测到 $PYTHON_VERSION"

# 检查 pip3
if ! command -v pip3 &> /dev/null; then
    echo "❌ 未检测到 pip3，请确保 Python3 安装完整"
    exit 1
fi

# 创建虚拟环境（推荐，避免污染系统Python）
echo ""
echo "正在创建虚拟环境 venv ..."
python3 -m venv venv
source venv/bin/activate

echo "✅ 虚拟环境创建成功"
echo ""
echo "正在安装依赖包（首次安装约需1-2分钟）..."
echo ""

pip install --upgrade pip -q
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 所有依赖安装成功！"
else
    echo ""
    echo "❌ 依赖安装失败，请检查网络连接后重试"
    exit 1
fi

# 复制配置文件
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "✅ 已创建配置文件 .env"
    echo "⚠️  请用文本编辑器打开 .env 文件，填写你的 API_KEY！"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  安装完成！接下来请按以下步骤操作：                       ║"
echo "║                                                          ║"
echo "║  1. 用文本编辑器打开 .env 文件，填写 API_KEY             ║"
echo "║  2. 将幕布导出的 PDF 文件放入 input_pdfs/ 目录           ║"
echo "║  3. 在终端运行：bash run.sh                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
