"""知识库 Service — CRUD、文档入库与混合检索。"""
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func

from ..config import Config
from ..db import KbDocument, KnowledgeBase, get_session
from .knowledge.chunker import split_text
from .knowledge.document_extractor import KbDocumentExtractor
from .knowledge.embedding_client import EmbeddingClient
from .knowledge.hybrid_search import HybridSearchEngine
from .knowledge.vector_store import VectorStore


class KnowledgeService:
    """知识库业务：元数据在 MySQL，向量 chunk 在 PostgreSQL。"""

    def __init__(self, config=None):
        self.config = config or Config()
        self.extractor = KbDocumentExtractor()
        self.embedding_client = EmbeddingClient(self.config)
        self.search_engine = HybridSearchEngine(self.config)
        self.vector_store = VectorStore(self.config)

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.upload_root = os.path.join(project_root, "uploads", "knowledge")
        os.makedirs(self.upload_root, exist_ok=True)

    def list_knowledge_bases(self, user_id: int) -> List[Dict]:
        db = get_session()
        try:
            rows = (
                db.query(KnowledgeBase)
                .filter(KnowledgeBase.user_id == user_id)
                .order_by(KnowledgeBase.updated_at.desc())
                .all()
            )
            return [self._serialize_kb(row) for row in rows]
        finally:
            db.close()

    def create_knowledge_base(self, user_id: int, name: str, description: str = "") -> Dict:
        name = (name or "").strip()
        if not name:
            raise ValueError("知识库名称不能为空")

        db = get_session()
        try:
            kb = KnowledgeBase(
                user_id=user_id,
                name=name[:200],
                description=(description or "").strip() or None,
            )
            db.add(kb)
            db.commit()
            db.refresh(kb)
            return self._serialize_kb(kb)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_knowledge_base(self, kb_id: int, user_id: int) -> Optional[Dict]:
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            return self._serialize_kb(kb) if kb else None
        finally:
            db.close()

    def update_knowledge_base(
        self,
        kb_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Dict]:
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                return None
            if name is not None:
                cleaned = name.strip()
                if not cleaned:
                    raise ValueError("知识库名称不能为空")
                kb.name = cleaned[:200]
            if description is not None:
                kb.description = description.strip() or None
            db.commit()
            db.refresh(kb)
            return self._serialize_kb(kb)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_knowledge_base(self, kb_id: int, user_id: int) -> bool:
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                return False

            docs = (
                db.query(KbDocument)
                .filter(
                    KbDocument.knowledge_base_id == kb_id,
                    KbDocument.user_id == user_id,
                )
                .all()
            )
            for doc in docs:
                self._remove_file(doc.file_path)
            self.vector_store.delete_chunks_for_kb(kb_id, user_id)
            db.delete(kb)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def list_documents(self, kb_id: int, user_id: int) -> List[Dict]:
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                return []
            rows = (
                db.query(KbDocument)
                .filter(
                    KbDocument.knowledge_base_id == kb_id,
                    KbDocument.user_id == user_id,
                )
                .order_by(KbDocument.created_at.desc())
                .all()
            )
            return [self._serialize_document(row) for row in rows]
        finally:
            db.close()

    def upload_document(self, kb_id: int, user_id: int, file_storage) -> Dict:
        if not file_storage or not file_storage.filename:
            raise ValueError("未选择文件")

        filename = file_storage.filename
        extension = os.path.splitext(filename)[1].lower()
        if not self.extractor.is_supported(extension):
            supported = ", ".join(self.extractor.get_supported_extensions())
            raise ValueError(f"不支持的文件格式，当前支持: {supported}")

        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)
        if file_size > self.config.MAX_FILE_SIZE:
            raise ValueError("文件大小超过限制")

        db = get_session()
        doc = None
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                raise ValueError("知识库不存在或无权限")

            kb_dir = os.path.join(self.upload_root, f"kb_{kb_id}")
            os.makedirs(kb_dir, exist_ok=True)
            stored_filename = f"{uuid.uuid4().hex}{extension}"
            file_path = os.path.join(kb_dir, stored_filename)
            file_storage.save(file_path)

            doc = KbDocument(
                knowledge_base_id=kb_id,
                user_id=user_id,
                original_filename=filename,
                stored_filename=stored_filename,
                file_path=file_path,
                file_size=file_size,
                file_extension=extension,
                status="processing",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            try:
                self._process_document(db, kb, doc)
            except Exception as exc:
                db.refresh(doc)
                raise ValueError(str(exc)) from exc

            db.refresh(doc)
            return self._serialize_document(doc)
        except ValueError:
            raise
        except Exception as exc:
            db.rollback()
            raise ValueError(str(exc)) from exc
        finally:
            db.close()

    def delete_document(self, kb_id: int, doc_id: int, user_id: int) -> bool:
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                return False
            doc = (
                db.query(KbDocument)
                .filter(
                    KbDocument.id == doc_id,
                    KbDocument.knowledge_base_id == kb_id,
                    KbDocument.user_id == user_id,
                )
                .first()
            )
            if not doc:
                return False

            self.vector_store.delete_chunks_for_document(doc.id)
            self._remove_file(doc.file_path)
            db.delete(doc)
            kb.document_count = max(0, (kb.document_count or 0) - 1)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def list_document_chunks(self, kb_id: int, doc_id: int, user_id: int) -> Optional[List[Dict]]:
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                return None
            doc = (
                db.query(KbDocument)
                .filter(
                    KbDocument.id == doc_id,
                    KbDocument.knowledge_base_id == kb_id,
                    KbDocument.user_id == user_id,
                )
                .first()
            )
            if not doc:
                return None

            chunks = self.vector_store.fetch_chunks_for_document(
                user_id=user_id,
                document_id=doc_id,
            )
            return [
                {
                    "id": item.get("id"),
                    "chunk_index": item.get("chunk_index"),
                    "content": item.get("content"),
                }
                for item in chunks
            ]
        finally:
            db.close()

    def update_document_chunk(
        self,
        kb_id: int,
        doc_id: int,
        chunk_id: int,
        user_id: int,
        content: str,
    ) -> Optional[Dict]:
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                return None
            doc = (
                db.query(KbDocument)
                .filter(
                    KbDocument.id == doc_id,
                    KbDocument.knowledge_base_id == kb_id,
                    KbDocument.user_id == user_id,
                )
                .first()
            )
            if not doc:
                return None

            updated = self.vector_store.update_chunk_content(
                chunk_id=chunk_id,
                user_id=user_id,
                document_id=doc_id,
                content=content,
            )
            if not updated:
                return None

            doc.status = "needs_reembedding"
            doc.error_message = None
            doc.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(doc)
            return {
                "chunk": {"id": chunk_id, "content": content.strip()},
                "document": self._serialize_document(doc),
            }
        except ValueError:
            raise
        except Exception as exc:
            db.rollback()
            raise ValueError(str(exc)) from exc
        finally:
            db.close()

    def reembed_document(self, kb_id: int, doc_id: int, user_id: int) -> Optional[Dict]:
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                return None
            doc = (
                db.query(KbDocument)
                .filter(
                    KbDocument.id == doc_id,
                    KbDocument.knowledge_base_id == kb_id,
                    KbDocument.user_id == user_id,
                )
                .first()
            )
            if not doc:
                return None

            chunks = self.vector_store.fetch_chunks_for_document(
                user_id=user_id,
                document_id=doc_id,
            )
            if not chunks:
                raise ValueError("没有可向量化的切片")

            doc.status = "processing"
            db.commit()

            texts = [item["content"] for item in chunks]
            embeddings = self.embedding_client.embed_texts(texts)
            if len(embeddings) != len(chunks):
                raise ValueError("向量化结果数量不匹配")

            self.vector_store.update_chunk_embeddings(
                user_id=user_id,
                document_id=doc_id,
                chunk_embeddings=[
                    (item["id"], embedding)
                    for item, embedding in zip(chunks, embeddings)
                ],
            )

            doc.status = "ready"
            doc.chunk_count = len(chunks)
            doc.error_message = None
            doc.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(doc)
            return self._serialize_document(doc)
        except Exception as exc:
            db.rollback()
            doc = (
                db.query(KbDocument)
                .filter(
                    KbDocument.id == doc_id,
                    KbDocument.knowledge_base_id == kb_id,
                    KbDocument.user_id == user_id,
                )
                .first()
            )
            if doc:
                doc.status = "needs_reembedding"
                doc.error_message = str(exc)[:500]
                db.commit()
            raise ValueError(str(exc)) from exc
        finally:
            db.close()

    def get_document_content(self, kb_id: int, doc_id: int, user_id: int) -> Optional[Dict]:
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                return None
            doc = (
                db.query(KbDocument)
                .filter(
                    KbDocument.id == doc_id,
                    KbDocument.knowledge_base_id == kb_id,
                    KbDocument.user_id == user_id,
                )
                .first()
            )
            if not doc:
                return None

            text, status = self.extractor.extract(doc.file_path, doc.file_extension)
            return {
                "document": self._serialize_document(doc),
                "content": text if status == "ready" else "",
            }
        finally:
            db.close()

    def get_enabled_document_ids(
        self, user_id: int, knowledge_base_ids: List[int]
    ) -> List[int]:
        db = get_session()
        try:
            rows = (
                db.query(KbDocument.id)
                .filter(
                    KbDocument.user_id == user_id,
                    KbDocument.knowledge_base_id.in_(knowledge_base_ids),
                    KbDocument.status == "ready",
                    KbDocument.is_enabled.is_(True),
                )
                .all()
            )
            return [row[0] for row in rows]
        finally:
            db.close()

    def update_documents_enabled(
        self,
        kb_id: int,
        user_id: int,
        document_ids: List[int],
        is_enabled: bool,
    ) -> int:
        if not document_ids:
            return 0
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                raise ValueError("知识库不存在或无权限")
            updated = (
                db.query(KbDocument)
                .filter(
                    KbDocument.knowledge_base_id == kb_id,
                    KbDocument.user_id == user_id,
                    KbDocument.id.in_(document_ids),
                )
                .update({KbDocument.is_enabled: is_enabled}, synchronize_session=False)
            )
            db.commit()
            return updated
        except ValueError:
            raise
        except Exception as exc:
            db.rollback()
            raise ValueError(str(exc)) from exc
        finally:
            db.close()

    def get_document_download(self, kb_id: int, doc_id: int, user_id: int) -> Optional[Dict]:
        db = get_session()
        try:
            kb = self._get_owned_kb(db, kb_id, user_id)
            if not kb:
                return None
            doc = (
                db.query(KbDocument)
                .filter(
                    KbDocument.id == doc_id,
                    KbDocument.knowledge_base_id == kb_id,
                    KbDocument.user_id == user_id,
                )
                .first()
            )
            if not doc or not doc.file_path or not os.path.exists(doc.file_path):
                return None
            return {
                "file_path": doc.file_path,
                "original_filename": doc.original_filename,
            }
        finally:
            db.close()

    def search(
        self,
        user_id: int,
        knowledge_base_ids: List[int],
        query: str,
        top_k: Optional[int] = None,
    ) -> Dict:
        query = (query or "").strip()
        if not query:
            raise ValueError("检索问题不能为空")
        if not knowledge_base_ids:
            raise ValueError("请至少选择一个知识库")

        validated_ids = self.validate_kb_access(user_id, knowledge_base_ids)
        enabled_doc_ids = self.get_enabled_document_ids(user_id, validated_ids)
        results = self.search_engine.search(
            user_id=user_id,
            knowledge_base_ids=validated_ids,
            query=query,
            top_k=top_k,
            enabled_document_ids=enabled_doc_ids,
        )
        return {
            "query": query,
            "knowledge_base_ids": validated_ids,
            "results": [
                {
                    "content": item.get("content"),
                    "filename": item.get("filename"),
                    "document_id": item.get("document_id"),
                    "chunk_index": item.get("chunk_index"),
                    "source": item.get("source"),
                    "fusion_score": item.get("fusion_score"),
                    "vector_score": item.get("vector_score"),
                    "bm25_score": item.get("bm25_score"),
                    "rerank_score": item.get("rerank_score"),
                }
                for item in results
            ],
            "formatted_context": HybridSearchEngine.format_results_for_agent(results),
        }

    def search_for_agent(
        self,
        user_id: int,
        knowledge_base_ids: List[int],
        query: str,
    ) -> str:
        try:
            payload = self.search(user_id, knowledge_base_ids, query)
            return payload["formatted_context"]
        except Exception as exc:
            return f"知识库检索失败: {exc}"

    def validate_kb_access(self, user_id: int, knowledge_base_ids: List[int]) -> List[int]:
        if not knowledge_base_ids:
            return []

        db = get_session()
        try:
            rows = (
                db.query(KnowledgeBase.id)
                .filter(
                    KnowledgeBase.user_id == user_id,
                    KnowledgeBase.id.in_(knowledge_base_ids),
                )
                .all()
            )
            return [row[0] for row in rows]
        finally:
            db.close()

    def get_supported_extensions(self) -> List[str]:
        return self.extractor.get_supported_extensions()

    def _process_document(self, db, kb: KnowledgeBase, doc: KbDocument) -> None:
        try:
            text, status = self.extractor.extract(doc.file_path, doc.file_extension)
            if status != "ready" or not text.strip():
                raise ValueError("无法从文档中提取文本")

            chunks = split_text(
                text,
                chunk_size=self.config.KB_CHUNK_SIZE,
                chunk_overlap=self.config.KB_CHUNK_OVERLAP,
            )
            if not chunks:
                raise ValueError("文档内容为空")

            self.vector_store.delete_chunks_for_document(doc.id)
            embeddings = self.embedding_client.embed_texts(chunks)
            chunk_count = self.vector_store.insert_chunks(
                document_id=doc.id,
                knowledge_base_id=kb.id,
                user_id=doc.user_id,
                chunks=chunks,
                embeddings=embeddings,
                filename=doc.original_filename,
            )

            doc.status = "ready"
            doc.chunk_count = chunk_count
            doc.error_message = None
            kb.document_count = (
                db.query(func.count(KbDocument.id))
                .filter(
                    KbDocument.knowledge_base_id == kb.id,
                    KbDocument.status == "ready",
                )
                .scalar()
                or 0
            )
            kb.updated_at = datetime.utcnow()
            db.commit()
        except Exception as exc:
            doc.status = "failed"
            doc.error_message = str(exc)[:500]
            db.commit()
            raise

    @staticmethod
    def _get_owned_kb(db, kb_id: int, user_id: int) -> Optional[KnowledgeBase]:
        return (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id)
            .first()
        )

    @staticmethod
    def _remove_file(file_path: str) -> None:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    @staticmethod
    def _serialize_kb(kb: KnowledgeBase) -> Dict:
        return {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "document_count": kb.document_count or 0,
            "created_at": kb.created_at.isoformat() if kb.created_at else None,
            "updated_at": kb.updated_at.isoformat() if kb.updated_at else None,
        }

    @staticmethod
    def _serialize_document(doc: KbDocument) -> Dict:
        return {
            "id": doc.id,
            "knowledge_base_id": doc.knowledge_base_id,
            "original_filename": doc.original_filename,
            "file_extension": doc.file_extension,
            "file_size": doc.file_size,
            "status": doc.status,
            "chunk_count": doc.chunk_count or 0,
            "is_enabled": bool(doc.is_enabled) if doc.is_enabled is not None else True,
            "error_message": doc.error_message,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        }
