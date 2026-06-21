"""知识库文档文本提取 — MVP 支持 txt / md / doc / docx。

职责总览：
1) 格式校验
   - `is_supported()` / `get_supported_extensions()`  判断扩展名是否支持
2) 文本提取
   - `extract()`  按扩展名调用对应解析器，返回 `(text, status)`

在入库流水线中的位置：
  上传文件 → extract → split_text → Embedding → VectorStore

支持格式：
- `.txt` / `.md`  直接按编码读取
- `.docx`         python-docx 解析段落
- `.doc`          antiword / catdoc 优先，失败则二进制兜底提取

已知局限与 TODO：
- TODO: 支持 PDF（PyMuPDF / pdfplumber）、XLSX、HTML 等常见格式
- TODO: `.doc` 依赖系统安装 antiword/catdoc；Docker 镜像需预装或统一转 docx
- TODO: 提取结果保留标题层级元数据，供分块与引用展示
- TODO: 大文件流式读取，避免一次性加载内存
- 局限: `.doc` 兜底方案为启发式二进制扫描，准确率低于正规解析器
- 局限: 仅提取纯文本，表格/图片内容会丢失
"""
import re
import subprocess
from pathlib import Path


KB_SUPPORTED_EXTENSIONS = {".txt", ".md", ".doc", ".docx"}


class KbDocumentExtractor:
    """按扩展名提取知识库文档纯文本。"""

    def is_supported(self, extension: str) -> bool:
        """判断文件扩展名是否在支持列表内。"""
        return extension.lower() in KB_SUPPORTED_EXTENSIONS

    def get_supported_extensions(self) -> list[str]:
        """返回支持的扩展名列表（含点号，如 `.md`）。"""
        return sorted(KB_SUPPORTED_EXTENSIONS)

    def extract(self, file_path: str, extension: str) -> tuple[str, str]:
        """从磁盘文件提取纯文本。

        用法:
        - 调用方: `KnowledgeService._process_document()`
        - 参数:
            - file_path: 已保存到 uploads 的本地路径
            - extension: 文件扩展名（如 `.md`）
        - 返回值: `(text, status)` — status 为 `ready` 或 `failed`
        """
        ext = extension.lower()
        if ext not in KB_SUPPORTED_EXTENSIONS:
            return "", "failed"

        try:
            if ext in {".txt", ".md"}:
                text = self._extract_text(file_path)
            elif ext == ".docx":
                text = self._extract_docx(file_path)
            elif ext == ".doc":
                text = self._extract_doc(file_path)
            else:
                return "", "failed"

            text = (text or "").strip()
            if not text:
                return "", "failed"
            return text, "ready"
        except Exception as exc:
            print(f"KB extract error ({file_path}): {exc}")
            return "", "failed"

    def _extract_text(self, file_path: str) -> str:
        """读取纯文本文件，依次尝试 utf-8 / gbk / gb2312 / latin-1。"""
        encodings = ["utf-8", "gbk", "gb2312", "latin-1"]
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as handle:
                    return handle.read()
            except UnicodeDecodeError:
                continue
        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
            return handle.read()

    def _extract_docx(self, file_path: str) -> str:
        """使用 python-docx 提取 .docx 段落文本。"""
        from docx import Document

        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)

    def _extract_doc(self, file_path: str) -> str:
        """提取旧版 .doc 文本：优先系统工具，失败则二进制兜底。

        TODO: 上传时自动将 .doc 转为 .docx 再入库
        """
        for command in (["antiword", file_path], ["catdoc", file_path]):
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            except FileNotFoundError:
                continue

        text = self._extract_doc_fallback(file_path)
        if text.strip():
            return text
        raise ValueError("无法解析 .doc 文件，请另存为 .docx 后重新上传")

    def _extract_doc_fallback(self, file_path: str) -> str:
        """尽力从旧版 .doc 二进制中提取可读文本（非精确，仅作兜底）。"""
        raw = Path(file_path).read_bytes()
        chunks = re.findall(rb"[\x20-\x7E\u4e00-\u9fff]{4,}", raw)
        if not chunks:
            return ""
        decoded = []
        for chunk in chunks[:500]:
            try:
                decoded.append(chunk.decode("utf-8"))
            except UnicodeDecodeError:
                decoded.append(chunk.decode("latin-1", errors="ignore"))
        return "\n".join(decoded)
