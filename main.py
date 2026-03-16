#!/usr/bin/env python3
"""
main.py
幕布知识库 AI 分析工具 - 主程序入口

使用方法：
  python3 main.py                    # 默认：批量分析 + 导出结果
  python3 main.py --mode summary     # 只做单篇摘要
  python3 main.py --mode global      # 只做全局分析（需先完成单篇摘要）
  python3 main.py --mode export      # 只导出已有结果为 Excel/Markdown
  python3 main.py --test             # 测试 API 连接是否正常
  python3 main.py --pdf /path/to/dir # 指定 PDF 目录
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 配置文件
load_dotenv()

from ai_client import AIClient
from analyzer import MubuAnalyzer


def setup_logging(output_dir: str):
    """配置日志输出：同时输出到控制台和日志文件。"""
    log_dir = Path(output_dir).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    from datetime import datetime
    log_file = log_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    return str(log_file)


def load_config() -> dict:
    """从环境变量加载配置，并做基本校验。"""
    config = {
        "api_key": os.getenv("API_KEY", ""),
        "base_url": os.getenv("BASE_URL", "https://api.deepseek.com/v1"),
        "model_name": os.getenv("MODEL_NAME", "deepseek-chat"),
        "chunk_size": int(os.getenv("CHUNK_SIZE", "3000")),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "200")),
        "request_delay": float(os.getenv("REQUEST_DELAY", "0.5")),
        "timeout": int(os.getenv("TIMEOUT", "120")),
        "pdf_input_dir": os.getenv("PDF_INPUT_DIR", "./input_pdfs"),
        "output_dir": os.getenv("OUTPUT_DIR", "./output"),
        "task_mode": os.getenv("TASK_MODE", "single_summary"),
        "resume": os.getenv("RESUME", "True").lower() == "true",
    }

    if not config["api_key"] or config["api_key"] == "你的API_Key填在这里":
        print("\n❌ 错误：请先在 .env 文件中填写你的 API_KEY！")
        print("   参考 .env.example 文件进行配置。\n")
        sys.exit(1)

    return config


def print_banner():
    """打印工具启动横幅。"""
    print("""
╔══════════════════════════════════════════════════════════╗
║          幕布知识库 AI 批量分析工具 v1.0                  ║
║          支持：ChatGPT / DeepSeek / Kimi / 通义 等        ║
╚══════════════════════════════════════════════════════════╝
""")


def main():
    print_banner()

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="幕布知识库 AI 批量分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["summary", "global", "export", "full"],
        default="full",
        help="运行模式：summary=单篇摘要, global=全局分析, export=导出结果, full=全流程（默认）",
    )
    parser.add_argument("--pdf", type=str, help="PDF 文件目录路径（覆盖 .env 中的配置）")
    parser.add_argument("--output", type=str, help="输出目录路径（覆盖 .env 中的配置）")
    parser.add_argument("--test", action="store_true", help="测试 API 连接是否正常")
    parser.add_argument("--no-resume", action="store_true", help="禁用断点续传，重新处理所有文件")
    args = parser.parse_args()

    # 加载配置
    config = load_config()

    # 命令行参数覆盖配置文件
    if args.pdf:
        config["pdf_input_dir"] = args.pdf
    if args.output:
        config["output_dir"] = args.output
    if args.no_resume:
        config["resume"] = False

    # 设置日志
    log_file = setup_logging(config["output_dir"])

    print(f"  模型：{config['model_name']}  |  接口：{config['base_url']}")
    print(f"  PDF目录：{config['pdf_input_dir']}")
    print(f"  输出目录：{config['output_dir']}")
    print(f"  断点续传：{'开启' if config['resume'] else '关闭'}")
    print(f"  日志文件：{log_file}\n")

    # 初始化 AI 客户端
    ai_client = AIClient(
        api_key=config["api_key"],
        base_url=config["base_url"],
        model_name=config["model_name"],
        timeout=config["timeout"],
        request_delay=config["request_delay"],
    )

    # 测试 API 连接
    if args.test:
        print("正在测试 API 连接...")
        if ai_client.test_connection():
            print("✅ API 连接正常！\n")
        else:
            print("❌ API 连接失败，请检查 API_KEY 和 BASE_URL 配置。\n")
        return

    # 初始化分析器
    analyzer = MubuAnalyzer(
        ai_client=ai_client,
        output_dir=config["output_dir"],
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
        resume=config["resume"],
    )

    mode = args.mode

    # ---- 执行单篇摘要分析 ----
    if mode in ("summary", "full"):
        print("【第一阶段】开始批量分析 PDF 文档...\n")
        results = analyzer.run_batch_analysis(config["pdf_input_dir"])
        success = sum(1 for r in results if r and r.get("status") == "success")
        print(f"\n✅ 本次处理完成：成功 {success} 篇")

    # ---- 执行全局汇总分析 ----
    if mode in ("global", "full"):
        print("\n【第二阶段】开始全局知识体系分析...\n")
        try:
            global_analysis = analyzer.run_global_analysis()
            global_report_path = Path(config["output_dir"]) / "全局知识体系分析.md"
            with open(global_report_path, "w", encoding="utf-8") as f:
                f.write("# 幕布知识库 - 全局知识体系分析\n\n")
                f.write(global_analysis)
            print(f"✅ 全局分析完成，已保存至：{global_report_path}")
        except FileNotFoundError as e:
            print(f"⚠️  {e}")
            global_analysis = ""
    else:
        global_analysis = ""

    # ---- 导出结果 ----
    if mode in ("export", "full", "summary"):
        print("\n【导出阶段】正在导出分析结果...\n")
        try:
            excel_path = analyzer.export_to_excel()
            print(f"✅ Excel 报告已保存：{excel_path}")
        except Exception as e:
            print(f"⚠️  Excel 导出失败：{e}")

        try:
            md_path = analyzer.export_to_markdown(global_analysis)
            print(f"✅ Markdown 报告已保存：{md_path}")
        except Exception as e:
            print(f"⚠️  Markdown 导出失败：{e}")

    print("\n" + "="*60)
    print("  全部任务完成！请查看 output/ 目录中的分析结果。")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
