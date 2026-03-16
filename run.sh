#!/bin/bash
# ============================================================
# 幕布AI分析工具 - 一键运行脚本
# ============================================================

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  未找到虚拟环境，请先运行 bash install_mac.sh"
    exit 1
fi

echo ""
echo "请选择运行模式："
echo "  1) 全流程（单篇摘要 + 全局分析 + 导出结果）【推荐】"
echo "  2) 仅单篇摘要（速度快，适合首次运行）"
echo "  3) 仅全局分析（需先完成单篇摘要）"
echo "  4) 仅导出已有结果为 Excel/Markdown"
echo "  5) 测试 API 连接"
echo ""
read -p "请输入数字 (1-5，默认1): " choice

case "${choice:-1}" in
    1) MODE="full" ;;
    2) MODE="summary" ;;
    3) MODE="global" ;;
    4) MODE="export" ;;
    5) python3 main.py --test; exit 0 ;;
    *) MODE="full" ;;
esac

echo ""
python3 main.py --mode "$MODE"
