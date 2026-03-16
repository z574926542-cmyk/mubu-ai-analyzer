"""
analyzer.py
核心分析逻辑模块
实现 Map-Reduce 式的批量文档分析流程：
  Map 阶段：对每篇文档单独分析，生成摘要
  Reduce 阶段：对所有摘要进行全局汇总分析
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
from tqdm import tqdm

from pdf_processor import process_pdf_to_chunks, scan_pdf_files
from ai_client import AIClient
from prompts import (
    SYSTEM_ROLE,
    SINGLE_DOC_SUMMARY_PROMPT,
    CHUNK_SUMMARY_PROMPT,
    GLOBAL_ANALYSIS_PROMPT,
    CLASSIFICATION_PROMPT,
)

logger = logging.getLogger(__name__)


class MubuAnalyzer:
    """
    幕布文档批量分析器。
    支持断点续传：已处理的文件会被记录，重新运行时自动跳过。
    """

    def __init__(
        self,
        ai_client: AIClient,
        output_dir: str,
        chunk_size: int = 3000,
        chunk_overlap: int = 200,
        resume: bool = True,
    ):
        self.ai = ai_client
        self.output_dir = Path(output_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.resume = resume

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 断点续传：记录已处理文件的进度文件
        self.progress_file = self.output_dir / "progress.json"
        self.progress = self._load_progress()

        # 结果存储文件
        self.results_file = self.output_dir / "results.jsonl"

    def _load_progress(self) -> Dict[str, bool]:
        """加载断点续传进度。"""
        if self.resume and self.progress_file.exists():
            with open(self.progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_progress(self, file_name: str):
        """保存单个文件的处理进度。"""
        self.progress[file_name] = True
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(self.progress, f, ensure_ascii=False, indent=2)

    def _append_result(self, result: Dict[str, Any]):
        """将单条结果追加写入 JSONL 文件（防止中途崩溃丢失数据）。"""
        with open(self.results_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    def _summarize_long_doc(self, chunks: List[str], file_name: str) -> str:
        """
        对超长文档（多个分块）进行两阶段总结：
        1. 先对每个分块生成摘要
        2. 再对所有分块摘要合并生成最终总结
        """
        if len(chunks) == 1:
            # 单块文档直接总结
            prompt = SINGLE_DOC_SUMMARY_PROMPT.format(content=chunks[0])
            return self.ai.chat(SYSTEM_ROLE, prompt)

        # 多块文档：先对每块做摘要
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            logger.debug(f"  正在处理 {file_name} 第 {i+1}/{len(chunks)} 块...")
            prompt = CHUNK_SUMMARY_PROMPT.format(content=chunk)
            summary = self.ai.chat(SYSTEM_ROLE, prompt)
            chunk_summaries.append(summary)

        # 再对所有分块摘要做最终总结
        combined = "\n\n---\n\n".join(chunk_summaries)
        final_prompt = SINGLE_DOC_SUMMARY_PROMPT.format(content=combined)
        return self.ai.chat(SYSTEM_ROLE, final_prompt)

    def analyze_single_doc(self, pdf_path: Path) -> Optional[Dict[str, Any]]:
        """
        分析单篇 PDF 文档：提取文本、分块、调用 AI 生成摘要。
        返回包含分析结果的字典。
        """
        file_name = pdf_path.name

        # 断点续传：跳过已处理的文件
        if self.resume and file_name in self.progress:
            logger.info(f"[跳过] {file_name}（已处理）")
            return None

        try:
            # 提取文本并分块
            doc_data = process_pdf_to_chunks(
                pdf_path,
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap,
            )

            if not doc_data["full_text"].strip():
                logger.warning(f"[警告] {file_name} 无法提取文本（可能是扫描件或图片PDF）")
                result = {
                    "file_name": file_name,
                    "file_path": str(pdf_path),
                    "total_chars": 0,
                    "chunk_count": 0,
                    "summary": "【无法提取文本：该PDF可能是扫描件或图片格式，需要OCR处理】",
                    "classification": "",
                    "processed_at": datetime.now().isoformat(),
                    "status": "skipped_no_text",
                }
                self._append_result(result)
                self._save_progress(file_name)
                return result

            # 调用 AI 生成摘要
            summary = self._summarize_long_doc(doc_data["chunks"], file_name)

            result = {
                "file_name": file_name,
                "file_path": str(pdf_path),
                "total_chars": doc_data["total_chars"],
                "chunk_count": doc_data["chunk_count"],
                "summary": summary,
                "classification": "",
                "processed_at": datetime.now().isoformat(),
                "status": "success",
            }

            self._append_result(result)
            self._save_progress(file_name)
            return result

        except Exception as e:
            logger.error(f"[错误] 处理 {file_name} 时出错: {e}")
            result = {
                "file_name": file_name,
                "file_path": str(pdf_path),
                "total_chars": 0,
                "chunk_count": 0,
                "summary": f"【处理失败: {str(e)}】",
                "classification": "",
                "processed_at": datetime.now().isoformat(),
                "status": "error",
            }
            self._append_result(result)
            return result

    def run_batch_analysis(self, pdf_dir: str) -> List[Dict[str, Any]]:
        """
        批量分析指定目录下的所有 PDF 文件（Map 阶段）。
        """
        pdf_files = scan_pdf_files(pdf_dir)
        total = len(pdf_files)

        if total == 0:
            logger.warning(f"在 {pdf_dir} 中未找到任何 PDF 文件！")
            return []

        # 统计已处理数量
        already_done = sum(1 for f in pdf_files if f.name in self.progress)
        remaining = total - already_done

        print(f"\n{'='*60}")
        print(f"  共发现 {total} 个 PDF 文件")
        print(f"  已处理: {already_done} 个  |  待处理: {remaining} 个")
        print(f"{'='*60}\n")

        results = []
        with tqdm(total=remaining, desc="分析进度", unit="篇") as pbar:
            for pdf_path in pdf_files:
                if self.resume and pdf_path.name in self.progress:
                    continue
                result = self.analyze_single_doc(pdf_path)
                if result:
                    results.append(result)
                    pbar.update(1)
                    pbar.set_postfix({"当前": pdf_path.name[:30]})

        return results

    def run_global_analysis(self) -> str:
        """
        全局汇总分析（Reduce 阶段）：
        读取所有单篇摘要，发给 AI 进行全局知识体系分析。
        """
        if not self.results_file.exists():
            raise FileNotFoundError("未找到单篇分析结果，请先运行批量分析。")

        # 读取所有成功处理的摘要
        summaries = []
        with open(self.results_file, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line.strip())
                if item.get("status") == "success" and item.get("summary"):
                    summaries.append(
                        f"【{item['file_name']}】\n{item['summary']}"
                    )

        if not summaries:
            return "没有可用于全局分析的摘要数据。"

        print(f"\n正在对 {len(summaries)} 篇文档进行全局分析，请稍候...\n")

        # 如果摘要总量太大，分批处理
        batch_size = 50  # 每批最多50篇
        batch_results = []

        for i in range(0, len(summaries), batch_size):
            batch = summaries[i:i + batch_size]
            combined = "\n\n" + "="*40 + "\n\n".join(batch)
            prompt = GLOBAL_ANALYSIS_PROMPT.format(
                doc_count=len(batch),
                summaries=combined,
            )
            print(f"  正在分析第 {i//batch_size + 1} 批（{len(batch)} 篇）...")
            result = self.ai.chat(SYSTEM_ROLE, prompt)
            batch_results.append(result)

        # 如果只有一批，直接返回
        if len(batch_results) == 1:
            return batch_results[0]

        # 多批次：对批次结果再做一次汇总
        print(f"\n  正在汇总 {len(batch_results)} 批分析结果...")
        final_combined = "\n\n---\n\n".join(batch_results)
        final_prompt = GLOBAL_ANALYSIS_PROMPT.format(
            doc_count=len(summaries),
            summaries=final_combined,
        )
        return self.ai.chat(SYSTEM_ROLE, final_prompt)

    def export_to_excel(self) -> str:
        """
        将所有分析结果导出为 Excel 文件，方便查阅和筛选。
        """
        if not self.results_file.exists():
            raise FileNotFoundError("未找到分析结果文件。")

        rows = []
        with open(self.results_file, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line.strip())
                rows.append({
                    "文件名": item.get("file_name", ""),
                    "字符数": item.get("total_chars", 0),
                    "分块数": item.get("chunk_count", 0),
                    "AI分析摘要": item.get("summary", ""),
                    "处理状态": item.get("status", ""),
                    "处理时间": item.get("processed_at", ""),
                })

        df = pd.DataFrame(rows)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = self.output_dir / f"幕布知识库分析结果_{timestamp}.xlsx"

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="分析结果")
            # 自动调整列宽
            worksheet = writer.sheets["分析结果"]
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max_len + 2, 80)

        return str(excel_path)

    def export_to_markdown(self, global_analysis: str = "") -> str:
        """
        将所有分析结果导出为 Markdown 报告。
        """
        if not self.results_file.exists():
            raise FileNotFoundError("未找到分析结果文件。")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = self.output_dir / f"幕布知识库分析报告_{timestamp}.md"

        lines = [
            f"# 幕布知识库分析报告",
            f"\n生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n",
        ]

        # 全局分析部分
        if global_analysis:
            lines.append("---\n")
            lines.append("## 全局知识体系分析\n")
            lines.append(global_analysis)
            lines.append("\n---\n")

        # 单篇分析部分
        lines.append("## 各文档分析详情\n")

        with open(self.results_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                item = json.loads(line.strip())
                lines.append(f"### {i}. {item.get('file_name', '未知文件')}\n")
                lines.append(f"- **字符数**：{item.get('total_chars', 0):,}")
                lines.append(f"- **处理状态**：{item.get('status', '')}\n")
                lines.append(item.get("summary", "（无摘要）"))
                lines.append("\n---\n")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return str(md_path)
