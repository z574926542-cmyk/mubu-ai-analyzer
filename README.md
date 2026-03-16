# 幕布知识库 AI 批量分析工具

> 专为幕布付费用户设计的本地 PDF 批量分析工具，支持几千篇文档、百万字级别的知识库处理。

[![Release](https://img.shields.io/github/v/release/z574926542-cmyk/mubu-ai-analyzer)](https://github.com/z574926542-cmyk/mubu-ai-analyzer/releases)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)](https://github.com/z574926542-cmyk/mubu-ai-analyzer/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

## 下载安装（Mac 用户直接下载）

前往 [Releases 页面](https://github.com/z574926542-cmyk/mubu-ai-analyzer/releases/latest) 下载最新版 `.dmg` 安装包，双击安装即可。

## 核心功能

- **PDF 批量提取**：高性能提取幕布导出的 PDF 文本，支持几千篇同时处理
- **智能长文本分块**：自动切分超长文档，保留上下文重叠，防止语义截断
- **多模型兼容**：支持 DeepSeek、Kimi、通义千问、ChatGPT、智谱 GLM 等所有兼容 OpenAI 接口的大模型
- **断点续传**：中途中断后下次自动跳过已处理文件
- **双层分析**：单篇摘要 + 全局知识体系分析
- **多格式导出**：结果导出为 Excel 表格和 Markdown 报告

## 支持的 AI 模型

| 模型 | 提供商 | API 地址 |
|------|--------|----------|
| deepseek-chat | DeepSeek | https://api.deepseek.com/v1 |
| moonshot-v1-128k | Kimi (月之暗面) | https://api.moonshot.cn/v1 |
| qwen-long | 通义千问 (阿里云) | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| gpt-4o | OpenAI | https://api.openai.com/v1 |
| glm-4-long | 智谱 AI | https://open.bigmodel.cn/api/paas/v4 |

## 快速开始（命令行方式）

```bash
# 1. 克隆仓库
git clone https://github.com/z574926542-cmyk/mubu-ai-analyzer.git
cd mubu-ai-analyzer

# 2. 一键安装依赖（Mac）
bash install_mac.sh

# 3. 配置 API Key
cp .env.example .env
# 用文本编辑器打开 .env，填入你的 API_KEY

# 4. 放入 PDF 文件
# 将幕布导出的 PDF 放入 input_pdfs/ 目录

# 5. 启动分析
bash run.sh
```

## 目录结构

```
mubu-ai-analyzer/
├── main.py              # 主程序入口
├── pdf_processor.py     # PDF 提取与分块
├── ai_client.py         # AI 接口封装（支持重试）
├── analyzer.py          # 核心分析逻辑（Map-Reduce）
├── prompts.py           # AI 提示词模板（可自定义）
├── .env.example         # 配置文件示例
├── requirements.txt     # Python 依赖
├── install_mac.sh       # Mac 一键安装脚本
├── run.sh               # 一键启动脚本
├── input_pdfs/          # 放入幕布导出的 PDF
└── output/              # 分析结果输出目录
```

## 自定义提示词

打开 `prompts.py` 文件，可以修改 AI 的分析指令，例如：
- 按特定维度分类打标
- 提取特定领域的知识点
- 生成结构化的知识图谱

## License

MIT
