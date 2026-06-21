"""文档分块 — 基于 LangChain RecursiveCharacterTextSplitter。

职责总览：
1) 文本切分
   - `split_text()`  将长文档拆为带重叠的 chunk 列表，供向量化与检索

在入库流水线中的位置（见 `knowledge_service._process_document`）：
  文档提取 → split_text → Embedding → 写入 VectorStore

相关配置（`Config` / `.env`）：
- `KB_CHUNK_SIZE`     单块最大字符数（默认 800）
- `KB_CHUNK_OVERLAP`  相邻块重叠字符数（默认 100，避免语义在边界断裂）

已知局限与 TODO：
- TODO: 按 token 数而非字符数分块，与 Embedding 模型上下文上限对齐
- TODO: 对 Markdown 按标题层级分块（HeaderTextSplitter），保留结构语义
- TODO: 表格 / 代码块作为原子单元，避免从中间切断
- 局限: `length_function=len` 按字符计数，中文长文可能超出 Embedding API token 上限
- 局限: 分隔符固定，对 PDF/HTML 等富文本需先归一化为纯文本
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """将长文本递归切分为多个 chunk。

    当前策略：
    - 优先按 `\n\n`、`\n`、中文句号等分隔符切分，尽量保持段落完整
    - 切分后去除首尾空白，过滤空串

    用法:
    - 调用方: `KnowledgeService._process_document()`
    - 参数:
        - text: 文档全文（已由 `KbDocumentExtractor` 提取）
        - chunk_size: 单块最大长度
        - chunk_overlap: 块间重叠长度
    - 返回值: 非空 chunk 字符串列表

    TODO:
    - 根据文件类型选择不同 splitter 策略
    - 超长单段无分隔符时记录告警日志
    """
    text = (text or "").strip()
    if not text:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", "；", ".", " ", ""],
    )
    return [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]
