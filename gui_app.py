#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
幕布知识库 AI 批量分析工具 - 图形界面版
双击即可运行，无需命令行
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# ── 数据目录（用户主目录下）──────────────────────────────
HOME = Path.home()
DATA_DIR = HOME / ".mubu_analyzer"
DATA_DIR.mkdir(exist_ok=True)
INPUT_DIR = DATA_DIR / "input_pdfs"
OUTPUT_DIR = DATA_DIR / "output"
LOG_DIR = DATA_DIR / "logs"
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
ENV_FILE = DATA_DIR / ".env"

# 如果没有 .env，从内置模板生成
if not ENV_FILE.exists():
    ENV_FILE.write_text(
        "API_KEY=你的API_Key填在这里\n"
        "BASE_URL=https://api.deepseek.com/v1\n"
        "MODEL_NAME=deepseek-chat\n"
        "CHUNK_SIZE=3000\n"
        "CONCURRENCY=3\n"
        "REQUEST_DELAY=0.5\n"
    )


def load_env():
    """读取 .env 配置"""
    cfg = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


def save_env(cfg: dict):
    """保存 .env 配置"""
    lines = []
    for k, v in cfg.items():
        lines.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── 颜色主题 ─────────────────────────────────────────────
BG = "#1e1e2e"
PANEL = "#2a2a3e"
ACCENT = "#7c6af7"
ACCENT2 = "#5bc4bf"
TEXT = "#cdd6f4"
TEXT_DIM = "#6c7086"
SUCCESS = "#a6e3a1"
WARNING = "#f9e2af"
ERROR = "#f38ba8"
BORDER = "#45475a"


class MubuAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("幕布知识库 AI 批量分析工具")
        self.geometry("900x680")
        self.minsize(800, 600)
        self.configure(bg=BG)

        # 设置 Mac 风格
        try:
            self.tk.call("::tk::unsupported::MacWindowStyle", "style", self._w, "document", "closeBox collapseBox resizeBox")
        except Exception:
            pass

        self._running = False
        self._thread = None
        self._cfg = load_env()

        self._build_ui()
        self._refresh_stats()

    # ── UI 构建 ───────────────────────────────────────────
    def _build_ui(self):
        # 顶部标题栏
        header = tk.Frame(self, bg=ACCENT, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="  幕布知识库 AI 批量分析工具", font=("PingFang SC", 16, "bold"),
                 bg=ACCENT, fg="white").pack(side="left", padx=16, pady=12)
        tk.Label(header, text="v1.1.0", font=("PingFang SC", 10),
                 bg=ACCENT, fg="#ddd").pack(side="right", padx=16)

        # 主体：左侧导航 + 右侧内容
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # 左侧导航
        nav = tk.Frame(body, bg=PANEL, width=180)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)

        self._nav_btns = {}
        nav_items = [
            ("📊  概览", "overview"),
            ("📁  PDF 文件", "files"),
            ("🤖  AI 配置", "config"),
            ("▶   开始分析", "run"),
            ("📄  查看结果", "results"),
        ]
        tk.Label(nav, text="功能菜单", font=("PingFang SC", 10),
                 bg=PANEL, fg=TEXT_DIM).pack(pady=(20, 8), padx=16, anchor="w")

        for label, key in nav_items:
            btn = tk.Button(nav, text=label, font=("PingFang SC", 12),
                            bg=PANEL, fg=TEXT, bd=0, padx=16, pady=10,
                            anchor="w", cursor="hand2",
                            activebackground=ACCENT, activeforeground="white",
                            command=lambda k=key: self._show_page(k))
            btn.pack(fill="x")
            self._nav_btns[key] = btn

        # 右侧内容区
        self._content = tk.Frame(body, bg=BG)
        self._content.pack(side="left", fill="both", expand=True)

        self._pages = {}
        self._build_overview()
        self._build_files()
        self._build_config()
        self._build_run()
        self._build_results()

        self._show_page("overview")

    def _show_page(self, key):
        for k, frame in self._pages.items():
            frame.pack_forget()
        for k, btn in self._nav_btns.items():
            btn.configure(bg=PANEL if k != key else ACCENT, fg=TEXT if k != key else "white")
        self._pages[key].pack(fill="both", expand=True, padx=20, pady=20)
        if key == "overview":
            self._refresh_stats()
        if key == "results":
            self._refresh_results()

    # ── 概览页 ────────────────────────────────────────────
    def _build_overview(self):
        page = tk.Frame(self._content, bg=BG)
        self._pages["overview"] = page

        tk.Label(page, text="📊 概览", font=("PingFang SC", 18, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 16))

        # 统计卡片行
        cards_row = tk.Frame(page, bg=BG)
        cards_row.pack(fill="x", pady=(0, 16))

        self._stat_pdf = self._stat_card(cards_row, "PDF 文件数", "0", ACCENT)
        self._stat_analyzed = self._stat_card(cards_row, "已分析", "0", ACCENT2)
        self._stat_chars = self._stat_card(cards_row, "预估字数", "—", WARNING)

        # 数据目录信息
        info_frame = tk.Frame(page, bg=PANEL, padx=16, pady=14)
        info_frame.pack(fill="x", pady=(0, 12))
        tk.Label(info_frame, text="📂 数据目录", font=("PingFang SC", 12, "bold"),
                 bg=PANEL, fg=TEXT).pack(anchor="w")
        tk.Label(info_frame, text=f"PDF 输入目录：{INPUT_DIR}",
                 font=("PingFang SC", 11), bg=PANEL, fg=TEXT_DIM).pack(anchor="w", pady=(4, 0))
        tk.Label(info_frame, text=f"分析结果目录：{OUTPUT_DIR}",
                 font=("PingFang SC", 11), bg=PANEL, fg=TEXT_DIM).pack(anchor="w")
        tk.Label(info_frame, text=f"配置文件：{ENV_FILE}",
                 font=("PingFang SC", 11), bg=PANEL, fg=TEXT_DIM).pack(anchor="w")

        btn_row = tk.Frame(page, bg=BG)
        btn_row.pack(fill="x", pady=(0, 12))
        self._mk_btn(btn_row, "📂 打开 PDF 目录", self._open_input_dir).pack(side="left", padx=(0, 8))
        self._mk_btn(btn_row, "📄 打开结果目录", self._open_output_dir).pack(side="left")

        # 使用说明
        guide = tk.Frame(page, bg=PANEL, padx=16, pady=14)
        guide.pack(fill="x")
        tk.Label(guide, text="🚀 快速开始", font=("PingFang SC", 12, "bold"),
                 bg=PANEL, fg=TEXT).pack(anchor="w")
        steps = [
            "① 点击左侧「AI 配置」，填入您的 AI API Key",
            "② 点击左侧「PDF 文件」，将幕布导出的 PDF 放入输入目录",
            "③ 点击左侧「开始分析」，选择分析模式并运行",
            "④ 分析完成后，点击「查看结果」查看摘要和报告",
        ]
        for s in steps:
            tk.Label(guide, text=s, font=("PingFang SC", 11),
                     bg=PANEL, fg=TEXT_DIM).pack(anchor="w", pady=2)

    def _stat_card(self, parent, label, value, color):
        card = tk.Frame(parent, bg=PANEL, padx=16, pady=12)
        card.pack(side="left", fill="x", expand=True, padx=(0, 8))
        lbl = tk.Label(card, text=value, font=("PingFang SC", 26, "bold"),
                       bg=PANEL, fg=color)
        lbl.pack(anchor="w")
        tk.Label(card, text=label, font=("PingFang SC", 10),
                 bg=PANEL, fg=TEXT_DIM).pack(anchor="w")
        return lbl

    def _refresh_stats(self):
        pdfs = list(INPUT_DIR.rglob("*.pdf"))
        self._stat_pdf.configure(text=str(len(pdfs)))
        results = list(OUTPUT_DIR.glob("*.jsonl"))
        analyzed = 0
        for r in results:
            try:
                analyzed += sum(1 for _ in r.read_text(encoding="utf-8").splitlines() if _.strip())
            except Exception:
                pass
        self._stat_analyzed.configure(text=str(analyzed))
        if pdfs:
            self._stat_chars.configure(text=f"~{len(pdfs) * 500:,}")

    # ── PDF 文件页 ────────────────────────────────────────
    def _build_files(self):
        page = tk.Frame(self._content, bg=BG)
        self._pages["files"] = page

        tk.Label(page, text="📁 PDF 文件管理", font=("PingFang SC", 18, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 12))

        btn_row = tk.Frame(page, bg=BG)
        btn_row.pack(fill="x", pady=(0, 12))
        self._mk_btn(btn_row, "➕ 添加 PDF 文件", self._add_pdfs).pack(side="left", padx=(0, 8))
        self._mk_btn(btn_row, "📂 打开 PDF 目录", self._open_input_dir).pack(side="left", padx=(0, 8))
        self._mk_btn(btn_row, "🔄 刷新列表", self._refresh_file_list).pack(side="left")

        info = tk.Label(page, text=f"PDF 目录：{INPUT_DIR}",
                        font=("PingFang SC", 10), bg=BG, fg=TEXT_DIM)
        info.pack(anchor="w", pady=(0, 8))

        # 文件列表
        list_frame = tk.Frame(page, bg=PANEL)
        list_frame.pack(fill="both", expand=True)

        cols = ("文件名", "大小", "路径")
        self._file_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=16)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, rowheight=28)
        style.configure("Treeview.Heading", background=BORDER, foreground=TEXT)

        for col in cols:
            self._file_tree.heading(col, text=col)
        self._file_tree.column("文件名", width=260)
        self._file_tree.column("大小", width=80)
        self._file_tree.column("路径", width=400)

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self._file_tree.yview)
        self._file_tree.configure(yscrollcommand=sb.set)
        self._file_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._file_count_lbl = tk.Label(page, text="共 0 个 PDF 文件",
                                        font=("PingFang SC", 10), bg=BG, fg=TEXT_DIM)
        self._file_count_lbl.pack(anchor="w", pady=(6, 0))
        self._refresh_file_list()

    def _refresh_file_list(self):
        for row in self._file_tree.get_children():
            self._file_tree.delete(row)
        pdfs = sorted(INPUT_DIR.rglob("*.pdf"))
        for p in pdfs:
            size = p.stat().st_size
            size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
            self._file_tree.insert("", "end", values=(p.name, size_str, str(p.parent)))
        self._file_count_lbl.configure(text=f"共 {len(pdfs)} 个 PDF 文件")

    def _add_pdfs(self):
        files = filedialog.askopenfilenames(
            title="选择幕布导出的 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if files:
            import shutil
            for f in files:
                shutil.copy(f, INPUT_DIR / Path(f).name)
            self._refresh_file_list()
            messagebox.showinfo("添加成功", f"已添加 {len(files)} 个 PDF 文件到分析目录")

    # ── AI 配置页 ─────────────────────────────────────────
    def _build_config(self):
        page = tk.Frame(self._content, bg=BG)
        self._pages["config"] = page

        tk.Label(page, text="🤖 AI 配置", font=("PingFang SC", 18, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 12))

        # 预设模型选择
        preset_frame = tk.Frame(page, bg=PANEL, padx=16, pady=14)
        preset_frame.pack(fill="x", pady=(0, 12))
        tk.Label(preset_frame, text="快速选择模型", font=("PingFang SC", 12, "bold"),
                 bg=PANEL, fg=TEXT).pack(anchor="w", pady=(0, 8))

        presets = [
            ("DeepSeek（推荐·性价比最高）", "https://api.deepseek.com/v1", "deepseek-chat"),
            ("Kimi 月之暗面（长文本强）", "https://api.moonshot.cn/v1", "moonshot-v1-128k"),
            ("通义千问（阿里云）", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-long"),
            ("ChatGPT（OpenAI）", "https://api.openai.com/v1", "gpt-4o"),
            ("智谱 GLM", "https://open.bigmodel.cn/api/paas/v4", "glm-4-long"),
        ]
        for name, url, model in presets:
            btn = tk.Button(preset_frame, text=name, font=("PingFang SC", 11),
                            bg=BORDER, fg=TEXT, bd=0, padx=12, pady=6, cursor="hand2",
                            activebackground=ACCENT, activeforeground="white",
                            command=lambda u=url, m=model: self._apply_preset(u, m))
            btn.pack(side="left", padx=(0, 8), pady=(0, 4))

        # 手动配置
        form_frame = tk.Frame(page, bg=PANEL, padx=16, pady=14)
        form_frame.pack(fill="x", pady=(0, 12))
        tk.Label(form_frame, text="手动配置", font=("PingFang SC", 12, "bold"),
                 bg=PANEL, fg=TEXT).pack(anchor="w", pady=(0, 10))

        fields = [
            ("API Key", "API_KEY", False),
            ("API 地址 (Base URL)", "BASE_URL", False),
            ("模型名称 (Model)", "MODEL_NAME", False),
            ("分块大小 (字符数)", "CHUNK_SIZE", False),
            ("并发数", "CONCURRENCY", False),
        ]
        self._cfg_vars = {}
        for label, key, is_pass in fields:
            row = tk.Frame(form_frame, bg=PANEL)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, font=("PingFang SC", 11), width=20,
                     bg=PANEL, fg=TEXT_DIM, anchor="w").pack(side="left")
            var = tk.StringVar(value=self._cfg.get(key, ""))
            show = "*" if is_pass else ""
            entry = tk.Entry(row, textvariable=var, font=("PingFang SC", 11),
                             bg=BORDER, fg=TEXT, insertbackground=TEXT,
                             relief="flat", bd=4, show=show)
            entry.pack(side="left", fill="x", expand=True)
            self._cfg_vars[key] = var

        btn_row = tk.Frame(page, bg=BG)
        btn_row.pack(fill="x", pady=(0, 12))
        self._mk_btn(btn_row, "💾 保存配置", self._save_config).pack(side="left", padx=(0, 8))
        self._mk_btn(btn_row, "🔗 测试 API 连接", self._test_api).pack(side="left")

        self._api_status = tk.Label(page, text="", font=("PingFang SC", 11), bg=BG, fg=TEXT_DIM)
        self._api_status.pack(anchor="w")

    def _apply_preset(self, url, model):
        self._cfg_vars["BASE_URL"].set(url)
        self._cfg_vars["MODEL_NAME"].set(model)

    def _save_config(self):
        for key, var in self._cfg_vars.items():
            self._cfg[key] = var.get().strip()
        save_env(self._cfg)
        messagebox.showinfo("保存成功", "配置已保存！")

    def _test_api(self):
        self._save_config()
        self._api_status.configure(text="⏳ 正在测试连接...", fg=WARNING)
        self.update()

        def do_test():
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=self._cfg.get("API_KEY", ""),
                    base_url=self._cfg.get("BASE_URL", "https://api.deepseek.com/v1")
                )
                resp = client.chat.completions.create(
                    model=self._cfg.get("MODEL_NAME", "deepseek-chat"),
                    messages=[{"role": "user", "content": "回复'OK'两个字"}],
                    max_tokens=10
                )
                result = resp.choices[0].message.content
                self._api_status.configure(text=f"✅ 连接成功！模型回复：{result}", fg=SUCCESS)
            except Exception as e:
                self._api_status.configure(text=f"❌ 连接失败：{str(e)[:80]}", fg=ERROR)

        threading.Thread(target=do_test, daemon=True).start()

    # ── 运行页 ────────────────────────────────────────────
    def _build_run(self):
        page = tk.Frame(self._content, bg=BG)
        self._pages["run"] = page

        tk.Label(page, text="▶  开始分析", font=("PingFang SC", 18, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 12))

        # 模式选择
        mode_frame = tk.Frame(page, bg=PANEL, padx=16, pady=14)
        mode_frame.pack(fill="x", pady=(0, 12))
        tk.Label(mode_frame, text="选择分析模式", font=("PingFang SC", 12, "bold"),
                 bg=PANEL, fg=TEXT).pack(anchor="w", pady=(0, 8))

        self._mode_var = tk.StringVar(value="full")
        modes = [
            ("full", "🔥 全流程（单篇摘要 + 全局分析 + 导出）【推荐】"),
            ("summary", "📝 仅单篇摘要（速度快，适合首次运行）"),
            ("global", "🌐 仅全局分析（需先完成单篇摘要）"),
            ("export", "📊 仅导出结果为 Excel / Markdown"),
        ]
        for val, label in modes:
            tk.Radiobutton(mode_frame, text=label, variable=self._mode_var, value=val,
                           font=("PingFang SC", 11), bg=PANEL, fg=TEXT,
                           selectcolor=ACCENT, activebackground=PANEL,
                           activeforeground=TEXT).pack(anchor="w", pady=2)

        # 控制按钮
        ctrl_row = tk.Frame(page, bg=BG)
        ctrl_row.pack(fill="x", pady=(0, 12))
        self._run_btn = self._mk_btn(ctrl_row, "▶  开始运行", self._start_analysis, color=ACCENT2)
        self._run_btn.pack(side="left", padx=(0, 8))
        self._stop_btn = self._mk_btn(ctrl_row, "⏹  停止", self._stop_analysis, color=ERROR)
        self._stop_btn.pack(side="left")
        self._stop_btn.configure(state="disabled")

        # 进度条
        prog_frame = tk.Frame(page, bg=BG)
        prog_frame.pack(fill="x", pady=(0, 8))
        self._progress_var = tk.DoubleVar()
        self._progress_bar = ttk.Progressbar(prog_frame, variable=self._progress_var,
                                              maximum=100, length=400)
        self._progress_bar.pack(side="left", fill="x", expand=True)
        self._progress_lbl = tk.Label(prog_frame, text="0%", font=("PingFang SC", 10),
                                      bg=BG, fg=TEXT_DIM, width=6)
        self._progress_lbl.pack(side="left", padx=(8, 0))

        # 日志输出
        tk.Label(page, text="运行日志", font=("PingFang SC", 11, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 4))
        self._log_text = scrolledtext.ScrolledText(
            page, font=("Menlo", 10), bg="#0d0d1a", fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=0, height=16
        )
        self._log_text.pack(fill="both", expand=True)
        self._log_text.configure(state="disabled")

    def _log(self, msg, color=None):
        self._log_text.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.insert("end", f"[{ts}] {msg}\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _start_analysis(self):
        pdfs = list(INPUT_DIR.rglob("*.pdf"))
        if not pdfs:
            messagebox.showwarning("无 PDF 文件", f"请先将幕布导出的 PDF 放入目录：\n{INPUT_DIR}")
            return
        api_key = self._cfg.get("API_KEY", "")
        if not api_key or "填在这里" in api_key:
            messagebox.showwarning("未配置 API Key", "请先在「AI 配置」页面填写您的 API Key！")
            self._show_page("config")
            return

        self._running = True
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._progress_var.set(0)
        self._log("=" * 50)
        self._log(f"开始分析，共 {len(pdfs)} 个 PDF 文件")
        self._log(f"模式：{self._mode_var.get()}")
        self._log(f"模型：{self._cfg.get('MODEL_NAME', 'deepseek-chat')}")

        mode = self._mode_var.get()
        self._thread = threading.Thread(target=self._run_analysis, args=(pdfs, mode), daemon=True)
        self._thread.start()

    def _stop_analysis(self):
        self._running = False
        self._log("⚠️  用户手动停止，等待当前任务完成...")
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")

    def _run_analysis(self, pdfs, mode):
        try:
            # 动态导入分析模块
            sys.path.insert(0, str(Path(__file__).parent))
            from pdf_processor import process_pdf_to_chunks
            from ai_client import AIClient
            from prompts import SUMMARY_PROMPT, GLOBAL_ANALYSIS_PROMPT

            client = AIClient(
                api_key=self._cfg.get("API_KEY", ""),
                base_url=self._cfg.get("BASE_URL", "https://api.deepseek.com/v1"),
                model=self._cfg.get("MODEL_NAME", "deepseek-chat"),
            )
            chunk_size = int(self._cfg.get("CHUNK_SIZE", 3000))

            results_file = OUTPUT_DIR / "summaries.jsonl"
            done_files = set()
            if results_file.exists():
                for line in results_file.read_text(encoding="utf-8").splitlines():
                    try:
                        done_files.add(json.loads(line)["file"])
                    except Exception:
                        pass

            total = len(pdfs)
            done = len(done_files)

            if mode in ("full", "summary"):
                with open(results_file, "a", encoding="utf-8") as fout:
                    for i, pdf_path in enumerate(pdfs):
                        if not self._running:
                            break
                        rel = str(pdf_path.relative_to(INPUT_DIR))
                        if rel in done_files:
                            self._log(f"⏭  跳过（已处理）：{pdf_path.name}")
                            done += 1
                            self._update_progress(done, total)
                            continue

                        self._log(f"📄 处理 [{i+1}/{total}]：{pdf_path.name}")
                        try:
                            data = process_pdf_to_chunks(pdf_path, chunk_size=chunk_size)
                            if not data["full_text"].strip():
                                self._log(f"   ⚠️  文本为空，跳过")
                                continue

                            # 对长文档分块摘要后合并
                            chunks = data["chunks"]
                            if len(chunks) == 1:
                                summary = client.chat(SUMMARY_PROMPT.format(
                                    title=pdf_path.stem, content=chunks[0]))
                            else:
                                chunk_summaries = []
                                for j, chunk in enumerate(chunks):
                                    if not self._running:
                                        break
                                    cs = client.chat(SUMMARY_PROMPT.format(
                                        title=f"{pdf_path.stem} (第{j+1}部分)", content=chunk))
                                    chunk_summaries.append(cs)
                                summary = client.chat(
                                    f"以下是同一篇文档的分段摘要，请综合成一份完整摘要：\n\n" +
                                    "\n\n---\n\n".join(chunk_summaries)
                                )

                            record = {
                                "file": rel,
                                "title": pdf_path.stem,
                                "chars": data["total_chars"],
                                "summary": summary,
                                "time": datetime.now().isoformat(),
                            }
                            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                            fout.flush()
                            done_files.add(rel)
                            done += 1
                            self._update_progress(done, total)
                            self._log(f"   ✅ 完成，摘要 {len(summary)} 字")
                            time.sleep(float(self._cfg.get("REQUEST_DELAY", 0.5)))
                        except Exception as e:
                            self._log(f"   ❌ 错误：{e}")

            if mode in ("full", "global") and self._running:
                self._log("\n🌐 开始全局分析...")
                summaries = []
                if results_file.exists():
                    for line in results_file.read_text(encoding="utf-8").splitlines():
                        try:
                            r = json.loads(line)
                            summaries.append(f"【{r['title']}】\n{r['summary']}")
                        except Exception:
                            pass
                if summaries:
                    combined = "\n\n".join(summaries[:100])  # 最多取100篇
                    global_report = client.chat(GLOBAL_ANALYSIS_PROMPT.format(summaries=combined))
                    report_file = OUTPUT_DIR / f"全局分析报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                    report_file.write_text(
                        f"# 幕布知识库全局分析报告\n\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n{global_report}",
                        encoding="utf-8"
                    )
                    self._log(f"✅ 全局报告已保存：{report_file.name}")

            if mode in ("full", "export") and self._running:
                self._log("\n📊 导出 Excel 报告...")
                self._export_excel(results_file)

            self._log("\n🎉 全部完成！")
            self._update_progress(100, 100)
            self.after(0, lambda: messagebox.showinfo("分析完成", "所有文件分析完成！\n点击「查看结果」查看报告。"))
            self.after(0, lambda: self._show_page("results"))

        except Exception as e:
            self._log(f"\n❌ 运行出错：{e}")
            import traceback
            self._log(traceback.format_exc())
        finally:
            self._running = False
            self.after(0, lambda: self._run_btn.configure(state="normal"))
            self.after(0, lambda: self._stop_btn.configure(state="disabled"))

    def _update_progress(self, done, total):
        pct = int(done / total * 100) if total > 0 else 0
        self.after(0, lambda: self._progress_var.set(pct))
        self.after(0, lambda: self._progress_lbl.configure(text=f"{pct}%"))

    def _export_excel(self, results_file):
        try:
            import pandas as pd
            rows = []
            if results_file.exists():
                for line in results_file.read_text(encoding="utf-8").splitlines():
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
            if rows:
                df = pd.DataFrame(rows)[["title", "chars", "summary", "time"]]
                df.columns = ["标题", "字数", "AI摘要", "分析时间"]
                out = OUTPUT_DIR / f"分析结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                df.to_excel(out, index=False)
                self._log(f"✅ Excel 已导出：{out.name}")
        except Exception as e:
            self._log(f"⚠️  Excel 导出失败：{e}")

    # ── 结果页 ────────────────────────────────────────────
    def _build_results(self):
        page = tk.Frame(self._content, bg=BG)
        self._pages["results"] = page

        tk.Label(page, text="📄 查看结果", font=("PingFang SC", 18, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 12))

        btn_row = tk.Frame(page, bg=BG)
        btn_row.pack(fill="x", pady=(0, 12))
        self._mk_btn(btn_row, "🔄 刷新", self._refresh_results).pack(side="left", padx=(0, 8))
        self._mk_btn(btn_row, "📂 打开结果目录", self._open_output_dir).pack(side="left")

        # 结果文件列表
        cols = ("文件名", "大小", "修改时间")
        self._result_tree = ttk.Treeview(page, columns=cols, show="headings", height=8)
        for col in cols:
            self._result_tree.heading(col, text=col)
        self._result_tree.column("文件名", width=300)
        self._result_tree.column("大小", width=80)
        self._result_tree.column("修改时间", width=160)
        self._result_tree.pack(fill="x", pady=(0, 12))
        self._result_tree.bind("<Double-1>", self._open_result_file)

        # 预览区
        tk.Label(page, text="内容预览（双击文件查看）", font=("PingFang SC", 11, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 4))
        self._preview_text = scrolledtext.ScrolledText(
            page, font=("PingFang SC", 10), bg=PANEL, fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=0, height=12
        )
        self._preview_text.pack(fill="both", expand=True)

    def _refresh_results(self):
        for row in self._result_tree.get_children():
            self._result_tree.delete(row)
        files = sorted(OUTPUT_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files:
            if f.is_file():
                size = f.stat().st_size
                size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                self._result_tree.insert("", "end", values=(f.name, size_str, mtime), tags=(str(f),))

    def _open_result_file(self, event):
        sel = self._result_tree.selection()
        if not sel:
            return
        item = self._result_tree.item(sel[0])
        fname = item["values"][0]
        fpath = OUTPUT_DIR / fname
        if fpath.suffix in (".md", ".jsonl", ".txt"):
            try:
                content = fpath.read_text(encoding="utf-8")
                self._preview_text.configure(state="normal")
                self._preview_text.delete("1.0", "end")
                self._preview_text.insert("end", content[:5000])
                if len(content) > 5000:
                    self._preview_text.insert("end", "\n\n... (内容过长，仅显示前5000字) ...")
                self._preview_text.configure(state="disabled")
            except Exception as e:
                self._preview_text.configure(state="normal")
                self._preview_text.delete("1.0", "end")
                self._preview_text.insert("end", f"读取失败：{e}")
                self._preview_text.configure(state="disabled")
        else:
            os.system(f'open "{fpath}"')

    # ── 工具方法 ──────────────────────────────────────────
    def _mk_btn(self, parent, text, cmd, color=ACCENT):
        return tk.Button(parent, text=text, font=("PingFang SC", 11),
                         bg=color, fg="white", bd=0, padx=14, pady=7,
                         cursor="hand2", activebackground=BORDER,
                         activeforeground="white", command=cmd)

    def _open_input_dir(self):
        os.system(f'open "{INPUT_DIR}"')

    def _open_output_dir(self):
        os.system(f'open "{OUTPUT_DIR}"')


def main():
    app = MubuAnalyzerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
