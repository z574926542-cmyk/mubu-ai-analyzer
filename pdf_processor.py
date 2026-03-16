"""
pdf_processor.py
PDF 文本提取与智能分块模块
"""

import re
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    从单个 PDF 文件中提取纯文本内容。
    使用 PyMuPDF，速度快，对中文支持好。
    """
    text_parts = []
    try:
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            if text.strip():
                text_parts.append(text)
        doc.close()
    except Exception as e:
        raise RuntimeError(f"读取 PDF 失败: {pdf_path}\n原因: {e}")

    full_text = "\n".join(text_parts)
    return clean_text(full_text)


def clean_text(text: str) -> str:
    """
    清洗提取出的文本：
    - 去除多余的空白行
    - 合并连续空格
    - 去除页眉页脚中常见的无意义字符
    """
    # 将多个连续空行压缩为最多一个空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 将多个连续空格压缩为一个
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # 去除行首行尾空白
    lines = [line.strip() for line in text.split('\n')]
    # 过滤掉只有1-2个字符的孤立行（通常是页码等噪音）
    lines = [line for line in lines if len(line) != 1]
    return '\n'.join(lines).strip()


def chunk_text(text: str, chunk_size: int = 3000, overlap: int = 200) -> List[str]:
    """
    将长文本按指定大小分块，相邻块之间有重叠以保持上下文连贯性。
    优先在段落边界（空行）处分割，保证语义完整。
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    paragraphs = text.split('\n\n')

    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 如果单个段落本身就超过了 chunk_size，则强制按字符切割
        if len(para) > chunk_size:
            # 先保存当前 chunk
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # 强制切割超长段落
            for i in range(0, len(para), chunk_size - overlap):
                sub_chunk = para[i:i + chunk_size]
                if sub_chunk.strip():
                    chunks.append(sub_chunk.strip())
            continue

        # 如果加入当前段落后超过了 chunk_size，先保存当前 chunk
        if len(current_chunk) + len(para) + 2 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                # 保留最后 overlap 个字符作为下一个 chunk 的开头（保持上下文）
                current_chunk = current_chunk[-overlap:] + "\n\n" + para if overlap > 0 else para
            else:
                current_chunk = para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def scan_pdf_files(input_dir: str) -> List[Path]:
    """
    递归扫描指定目录下的所有 PDF 文件，返回文件路径列表。
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")

    pdf_files = sorted(input_path.rglob("*.pdf"))
    return pdf_files


def process_pdf_to_chunks(
    pdf_path: Path,
    chunk_size: int = 3000,
    overlap: int = 200
) -> Dict[str, Any]:
    """
    处理单个 PDF 文件：提取文本并分块。
    返回包含文件信息和文本块的字典。
    """
    text = extract_text_from_pdf(str(pdf_path))
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    return {
        "file_name": pdf_path.name,
        "file_path": str(pdf_path),
        "total_chars": len(text),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "full_text": text,
    }
