"""知识库 API 路由。

接口总览（按用户使用流程）：
1) 知识库管理
   - GET    `/api/knowledge-bases`              列出当前用户的知识库
   - POST   `/api/knowledge-bases`              创建知识库
   - GET    `/api/knowledge-bases/<kb_id>`      获取知识库详情
   - PATCH  `/api/knowledge-bases/<kb_id>`      更新知识库名称/描述
   - DELETE `/api/knowledge-bases/<kb_id>`      删除知识库及向量数据
2) 文档管理
   - GET    `/api/knowledge-bases/<kb_id>/documents`                  列出文档
   - POST   `/api/knowledge-bases/<kb_id>/documents`                  上传文档并入库
   - DELETE `/api/knowledge-bases/<kb_id>/documents/<doc_id>`         删除文档
3) 检索与配置
   - POST   `/api/knowledge-bases/<kb_id>/search`  混合检索测试
   - GET    `/api/knowledge/supported`               支持的文件类型与大小限制
"""
from flask import Blueprint, jsonify, request, send_file

from ..services.auth_token import login_required
from ..services.knowledge_service import KnowledgeService
from ..utils import get_current_user

knowledge_bp = Blueprint("knowledge", __name__)


def _service() -> KnowledgeService:
    """获取知识库 Service 实例。"""
    return KnowledgeService()


@knowledge_bp.route("/knowledge-bases", methods=["GET"])
@login_required
def list_knowledge_bases():
    """列出当前用户的全部知识库。

    用法:
    - 方法/路径: `GET /api/knowledge-bases`
    - 认证: Bearer Token
    - 成功响应: `{ "knowledge_bases": [...] }`
    - 失败响应: 401 未登录
    ---
    tags:
      - 知识库
    summary: 获取知识库列表
    produces:
      - application/json
    security:
      - bearerAuth: []
    responses:
      200:
        description: 获取成功
      401:
        description: 未登录
    """
    user = get_current_user()

    service = _service()
    return jsonify({"knowledge_bases": service.list_knowledge_bases(user["id"])})


@knowledge_bp.route("/knowledge-bases", methods=["POST"])
@login_required
def create_knowledge_base():
    """创建知识库。

    用法:
    - 方法/路径: `POST /api/knowledge-bases`
    - 认证: Bearer Token
    - 请求体: `{ "name": "...", "description": "..." }`
    - 成功响应: `{ "success": true, "knowledge_base": {...} }`
    - 失败响应: 400 参数错误；401 未登录；500 创建失败
    ---
    tags:
      - 知识库
    summary: 创建知识库
    consumes:
      - application/json
    produces:
      - application/json
    security:
      - bearerAuth: []
    responses:
      200:
        description: 创建成功
      400:
        description: 参数错误
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    user = get_current_user()

    data = request.get_json(silent=True) or {}
    try:
        kb = _service().create_knowledge_base(
            user_id=user["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
        )
        return jsonify({"success": True, "knowledge_base": kb})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"创建失败: {exc}"}), 500


@knowledge_bp.route("/knowledge-bases/<int:kb_id>", methods=["GET"])
@login_required
def get_knowledge_base(kb_id):
    """获取指定知识库详情。

    用法:
    - 方法/路径: `GET /api/knowledge-bases/<kb_id>`
    - 认证: Bearer Token
    - 成功响应: `{ "id", "name", "description", "document_count", ... }`
    - 失败响应: 401 未登录；404 知识库不存在或无权限
    ---
    tags:
      - 知识库
    summary: 获取知识库详情
    produces:
      - application/json
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: kb_id
        type: integer
        required: true
        description: 知识库 ID
    responses:
      200:
        description: 获取成功
      401:
        description: 未登录
      404:
        description: 知识库不存在或无权限
    """
    user = get_current_user()

    kb = _service().get_knowledge_base(kb_id, user["id"])
    if not kb:
        return jsonify({"error": "知识库不存在或无权限"}), 404
    return jsonify(kb)


@knowledge_bp.route("/knowledge-bases/<int:kb_id>", methods=["PATCH"])
@login_required
def update_knowledge_base(kb_id):
    """更新知识库名称或描述。

    用法:
    - 方法/路径: `PATCH /api/knowledge-bases/<kb_id>`
    - 认证: Bearer Token
    - 请求体: `{ "name": "...", "description": "..." }`（字段可选）
    - 成功响应: `{ "success": true, "knowledge_base": {...} }`
    - 失败响应: 400 参数错误；401 未登录；404 不存在；500 更新失败
    ---
    tags:
      - 知识库
    summary: 更新知识库
    consumes:
      - application/json
    produces:
      - application/json
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: kb_id
        type: integer
        required: true
        description: 知识库 ID
    responses:
      200:
        description: 更新成功
      400:
        description: 参数错误
      401:
        description: 未登录
      404:
        description: 知识库不存在或无权限
      500:
        description: 服务器内部错误
    """
    user = get_current_user()

    data = request.get_json(silent=True) or {}
    try:
        kb = _service().update_knowledge_base(
            kb_id=kb_id,
            user_id=user["id"],
            name=data.get("name"),
            description=data.get("description"),
        )
        if not kb:
            return jsonify({"error": "知识库不存在或无权限"}), 404
        return jsonify({"success": True, "knowledge_base": kb})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"更新失败: {exc}"}), 500


@knowledge_bp.route("/knowledge-bases/<int:kb_id>", methods=["DELETE"])
@login_required
def delete_knowledge_base(kb_id):
    """删除知识库及其全部文档与向量数据。

    用法:
    - 方法/路径: `DELETE /api/knowledge-bases/<kb_id>`
    - 认证: Bearer Token
    - 成功响应: `{ "success": true }`
    - 失败响应: 401 未登录；404 不存在；500 删除失败
    ---
    tags:
      - 知识库
    summary: 删除知识库
    produces:
      - application/json
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: kb_id
        type: integer
        required: true
        description: 知识库 ID
    responses:
      200:
        description: 删除成功
      401:
        description: 未登录
      404:
        description: 知识库不存在或无权限
      500:
        description: 服务器内部错误
    """
    user = get_current_user()

    try:
        ok = _service().delete_knowledge_base(kb_id, user["id"])
        if not ok:
            return jsonify({"error": "知识库不存在或无权限"}), 404
        return jsonify({"success": True})
    except Exception as exc:
        return jsonify({"error": f"删除失败: {exc}"}), 500


@knowledge_bp.route("/knowledge-bases/<int:kb_id>/documents", methods=["GET"])
@login_required
def list_documents(kb_id):
    """列出知识库下的全部文档。

    用法:
    - 方法/路径: `GET /api/knowledge-bases/<kb_id>/documents`
    - 认证: Bearer Token
    - 成功响应: `{ "documents": [...] }`
    - 失败响应: 401 未登录；404 知识库不存在或无权限
    ---
    tags:
      - 知识库
    summary: 获取文档列表
    produces:
      - application/json
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: kb_id
        type: integer
        required: true
        description: 知识库 ID
    responses:
      200:
        description: 获取成功
      401:
        description: 未登录
      404:
        description: 知识库不存在或无权限
    """
    user = get_current_user()

    service = _service()
    if not service.get_knowledge_base(kb_id, user["id"]):
        return jsonify({"error": "知识库不存在或无权限"}), 404
    return jsonify({"documents": service.list_documents(kb_id, user["id"])})


@knowledge_bp.route("/knowledge-bases/<int:kb_id>/documents", methods=["POST"])
@login_required
def upload_document(kb_id):
    """上传文档到知识库（解析、分块、向量化入库）。

    用法:
    - 方法/路径: `POST /api/knowledge-bases/<kb_id>/documents`
    - 认证: Bearer Token
    - 请求体: `multipart/form-data`，字段 `file`
    - 成功响应: `{ "success": true, "document": {...} }`
    - 失败响应: 400 无文件或格式不支持；401 未登录；500 上传/入库失败
    ---
    tags:
      - 知识库
    summary: 上传文档
    consumes:
      - multipart/form-data
    produces:
      - application/json
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: kb_id
        type: integer
        required: true
        description: 知识库 ID
      - in: formData
        name: file
        type: file
        required: true
        description: 待入库的文档文件
    responses:
      200:
        description: 上传成功
      400:
        description: 参数错误或文件格式不支持
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    user = get_current_user()

    if "file" not in request.files:
        return jsonify({"error": "没有上传文件"}), 400

    file = request.files["file"]
    try:
        doc = _service().upload_document(kb_id, user["id"], file)
        return jsonify({"success": True, "document": doc})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"上传失败: {exc}"}), 500


@knowledge_bp.route("/knowledge-bases/<int:kb_id>/documents/<int:doc_id>", methods=["DELETE"])
@login_required
def delete_document(kb_id, doc_id):
    """删除知识库中的指定文档。

    用法:
    - 方法/路径: `DELETE /api/knowledge-bases/<kb_id>/documents/<doc_id>`
    - 认证: Bearer Token
    - 成功响应: `{ "success": true }`
    - 失败响应: 401 未登录；404 文档不存在；500 删除失败
    ---
    tags:
      - 知识库
    summary: 删除文档
    produces:
      - application/json
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: kb_id
        type: integer
        required: true
        description: 知识库 ID
      - in: path
        name: doc_id
        type: integer
        required: true
        description: 文档 ID
    responses:
      200:
        description: 删除成功
      401:
        description: 未登录
      404:
        description: 文档不存在或无权限
      500:
        description: 服务器内部错误
    """
    user = get_current_user()

    try:
        ok = _service().delete_document(kb_id, doc_id, user["id"])
        if not ok:
            return jsonify({"error": "文档不存在或无权限"}), 404
        return jsonify({"success": True})
    except Exception as exc:
        return jsonify({"error": f"删除失败: {exc}"}), 500


@knowledge_bp.route(
    "/knowledge-bases/<int:kb_id>/documents/<int:doc_id>/chunks/<int:chunk_id>",
    methods=["PATCH"],
)
@login_required
def update_document_chunk(kb_id, doc_id, chunk_id):
    """编辑指定切片内容，文档将进入待重新向量化状态。"""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")

    try:
        result = _service().update_document_chunk(
            kb_id=kb_id,
            doc_id=doc_id,
            chunk_id=chunk_id,
            user_id=user["id"],
            content=content,
        )
        if not result:
            return jsonify({"error": "切片或文档不存在"}), 404
        return jsonify({"success": True, **result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"更新失败: {exc}"}), 500


@knowledge_bp.route("/knowledge-bases/<int:kb_id>/documents/<int:doc_id>/reembed", methods=["POST"])
@login_required
def reembed_document(kb_id, doc_id):
    """对文档全部切片重新向量化。"""
    user = get_current_user()

    try:
        doc = _service().reembed_document(kb_id, doc_id, user["id"])
        if not doc:
            return jsonify({"error": "文档不存在或无权限"}), 404
        return jsonify({"success": True, "document": doc})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"向量化失败: {exc}"}), 500


@knowledge_bp.route("/knowledge-bases/<int:kb_id>/documents/batch", methods=["PATCH"])
@login_required
def batch_update_documents(kb_id):
    """批量启用或禁用文档。"""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    document_ids = data.get("document_ids") or []
    if not isinstance(document_ids, list) or not document_ids:
        return jsonify({"error": "请选择至少一个文档"}), 400
    if "is_enabled" not in data:
        return jsonify({"error": "缺少 is_enabled 参数"}), 400

    try:
        updated = _service().update_documents_enabled(
            kb_id=kb_id,
            user_id=user["id"],
            document_ids=[int(doc_id) for doc_id in document_ids],
            is_enabled=bool(data.get("is_enabled")),
        )
        return jsonify({"success": True, "updated": updated})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"更新失败: {exc}"}), 500


@knowledge_bp.route("/knowledge-bases/<int:kb_id>/documents/<int:doc_id>/download", methods=["GET"])
@login_required
def download_document(kb_id, doc_id):
    """下载原始文档文件。"""
    user = get_current_user()
    payload = _service().get_document_download(kb_id, doc_id, user["id"])
    if not payload:
        return jsonify({"error": "文档不存在或文件已丢失"}), 404
    return send_file(
        payload["file_path"],
        as_attachment=True,
        download_name=payload["original_filename"],
    )


@knowledge_bp.route("/knowledge-bases/<int:kb_id>/documents/<int:doc_id>/chunks", methods=["GET"])
@login_required
def list_document_chunks(kb_id, doc_id):
    """列出指定文档的全部分块。"""
    user = get_current_user()

    chunks = _service().list_document_chunks(kb_id, doc_id, user["id"])
    if chunks is None:
        return jsonify({"error": "文档不存在或无权限"}), 404
    return jsonify({"chunks": chunks})


@knowledge_bp.route("/knowledge-bases/<int:kb_id>/documents/<int:doc_id>/content", methods=["GET"])
@login_required
def get_document_content(kb_id, doc_id):
    """获取文档原文（用于切片预览）。"""
    user = get_current_user()

    payload = _service().get_document_content(kb_id, doc_id, user["id"])
    if not payload:
        return jsonify({"error": "文档不存在或无权限"}), 404
    return jsonify(payload)


@knowledge_bp.route("/knowledge-bases/<int:kb_id>/search", methods=["POST"])
@login_required
def search_knowledge_base(kb_id):
    """在指定知识库中执行混合检索（向量 + BM25 + Rerank）。

    用法:
    - 方法/路径: `POST /api/knowledge-bases/<kb_id>/search`
    - 认证: Bearer Token
    - 请求体: `{ "query": "...", "top_k": 5 }`
    - 成功响应: `{ "success": true, "query", "results", "formatted_context" }`
    - 失败响应: 400 参数错误；401 未登录；500 检索失败
    ---
    tags:
      - 知识库
    summary: 知识库检索
    consumes:
      - application/json
    produces:
      - application/json
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: kb_id
        type: integer
        required: true
        description: 知识库 ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - query
          properties:
            query:
              type: string
              description: 检索问题
            top_k:
              type: integer
              description: 返回条数（可选）
    responses:
      200:
        description: 检索成功
      400:
        description: 参数错误
      401:
        description: 未登录
      500:
        description: 检索失败
    """
    user = get_current_user()

    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    top_k = data.get("top_k")

    try:
        result = _service().search(
            user_id=user["id"],
            knowledge_base_ids=[kb_id],
            query=query,
            top_k=top_k,
        )
        return jsonify({"success": True, **result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"检索失败: {exc}"}), 500


@knowledge_bp.route("/knowledge/supported", methods=["GET"])
def supported_extensions():
    """获取知识库支持的文件扩展名与大小限制（公开接口）。

    用法:
    - 方法/路径: `GET /api/knowledge/supported`
    - 认证: 无需登录
    - 成功响应: `{ "extensions": [...], "max_size_mb": 100 }`
    ---
    tags:
      - 知识库
    summary: 获取支持的文档类型
    produces:
      - application/json
    responses:
      200:
        description: 获取成功
    """
    service = _service()
    return jsonify(
        {
            "extensions": [ext.lstrip(".") for ext in service.get_supported_extensions()],
            "max_size_mb": service.config.MAX_FILE_SIZE // (1024 * 1024),
        }
    )
