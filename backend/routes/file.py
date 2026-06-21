"""文件管理 API 路由。"""
import os

from flask import Blueprint, jsonify, request, send_file

from ..db import get_session
from ..db import UploadedFile
from ..services import FileService
from ..utils import get_current_user

file_bp = Blueprint("file", __name__)


@file_bp.route('/files', methods=['POST'])
def upload_file():
    """上传文件到服务器。

    用法:
    - 方法/路径: `POST /api/files`
    - 认证: Bearer Token
    - 请求体: `multipart/form-data`，字段 `file`
    - 成功响应: `{ "success": true, "file_id": 1, "filename": "...", ... }`
    - 失败响应: 401 未登录；400 无文件或格式错误；500 上传失败
    ---
    tags:
      - 文件
    summary: 上传文件
    description: |
      上传文件到服务器，支持 PDF、DOCX、XLSX、TXT 等格式。
      文件大小限制：100MB
      上传成功后返回文件ID，可用于聊天时附加文件。
    consumes:
      - multipart/form-data
    produces:
      - application/json
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: 要上传的文件
    responses:
      200:
        description: 上传成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            file_id:
              type: integer
              description: 文件ID
              example: 1
            filename:
              type: string
              description: 文件名
              example: "document.pdf"
            file_type:
              type: string
              description: 文件类型
              example: "pdf"
            file_size:
              type: integer
              description: 文件大小（字节）
              example: 1024000
            message:
              type: string
              example: "文件上传成功"
        examples:
          application/json:
            success: true
            file_id: 1
            filename: "document.pdf"
            file_type: "pdf"
            file_size: 1024000
            message: "文件上传成功"
      400:
        description: 请求参数错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: "没有上传文件"
      401:
        description: 未登录
        schema:
          type: object
          properties:
            error:
              type: string
              example: "未登录"
      500:
        description: 服务器内部错误
    security:
      - bearerAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': '文件名为空'}), 400
        
        file_service = FileService()
        result = file_service.save_file(user['id'], file)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        print(f"Upload file error: {e}")
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


@file_bp.route('/files', methods=['GET'])
def get_files():
    """获取当前用户上传的全部文件。

    用法:
    - 方法/路径: `GET /api/files`
    - 认证: Bearer Token
    - 成功响应: `{ "files": [...] }`
    - 失败响应: 401 未登录；500 获取失败
    ---
    tags:
      - 文件
    summary: 获取当前用户的所有文件
    description: 返回当前登录用户上传的所有文件列表
    produces:
      - application/json
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            files:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: 文件ID
                    example: 1
                  filename:
                    type: string
                    description: 文件名
                    example: "document.pdf"
                  file_type:
                    type: string
                    description: 文件类型
                    example: "pdf"
                  file_size:
                    type: integer
                    description: 文件大小（字节）
                    example: 1024000
                  created_at:
                    type: string
                    format: date-time
                    description: 上传时间
                    example: "2024-01-01T12:00:00"
        examples:
          application/json:
            files:
              - id: 1
                filename: "document.pdf"
                file_type: "pdf"
                file_size: 1024000
                created_at: "2024-01-01T12:00:00"
      401:
        description: 未登录
        schema:
          type: object
          properties:
            error:
              type: string
              example: "未登录"
      500:
        description: 服务器内部错误
    security:
      - bearerAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        file_service = FileService()
        files = file_service.get_user_files(user['id'])
        return jsonify({'files': files})
    except Exception as e:
        print(f"Get files error: {e}")
        return jsonify({'error': '获取文件列表失败'}), 500


@file_bp.route('/files/<int:file_id>', methods=['GET'])
def get_file(file_id):
    """获取指定文件的详细信息。

    用法:
    - 方法/路径: `GET /api/files/<file_id>`
    - 认证: Bearer Token
    - 成功响应: `{ "id": 1, "filename": "...", "content_preview": "...", ... }`
    - 失败响应: 401 未登录；404 文件不存在或无权限；500 获取失败
    ---
    tags:
      - 文件
    summary: 获取指定文件的详细信息
    description: 返回指定文件的详细信息，包括文件内容摘要等
    produces:
      - application/json
    parameters:
      - in: path
        name: file_id
        type: integer
        required: true
        description: 文件ID
        example: 1
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            id:
              type: integer
              description: 文件ID
              example: 1
            filename:
              type: string
              description: 文件名
              example: "document.pdf"
            file_type:
              type: string
              description: 文件类型
              example: "pdf"
            file_size:
              type: integer
              description: 文件大小（字节）
              example: 1024000
            created_at:
              type: string
              format: date-time
              description: 上传时间
              example: "2024-01-01T12:00:00"
            content_preview:
              type: string
              description: 文件内容预览
              example: "这是文件的前500个字符..."
      401:
        description: 未登录
        schema:
          type: object
          properties:
            error:
              type: string
              example: "未登录"
      404:
        description: 文件不存在或无权限
        schema:
          type: object
          properties:
            error:
              type: string
              example: "文件不存在或无权限"
      500:
        description: 服务器内部错误
    security:
      - bearerAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        file_service = FileService()
        file_info = file_service.get_file(file_id, user['id'])
        
        if not file_info:
            return jsonify({'error': '文件不存在或无权限'}), 404
        
        return jsonify(file_info)
    except Exception as e:
        print(f"Get file error: {e}")
        return jsonify({'error': '获取文件信息失败'}), 500


@file_bp.route('/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """删除当前用户拥有的指定文件。

    用法:
    - 方法/路径: `DELETE /api/files/<file_id>`
    - 认证: Bearer Token
    - 成功响应: `{ "success": true }`
    - 失败响应: 401 未登录；400 文件不存在或无权限；500 删除失败
    ---
    tags:
      - 文件
    summary: 删除指定文件
    description: 删除用户上传的指定文件，只能删除自己的文件
    produces:
      - application/json
    parameters:
      - in: path
        name: file_id
        type: integer
        required: true
        description: 文件ID
        example: 1
    responses:
      200:
        description: 删除成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
        examples:
          application/json:
            success: true
      400:
        description: 删除失败
        schema:
          type: object
          properties:
            error:
              type: string
              example: "文件不存在或无权限"
      401:
        description: 未登录
        schema:
          type: object
          properties:
            error:
              type: string
              example: "未登录"
      500:
        description: 服务器内部错误
    security:
      - bearerAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        file_service = FileService()
        result = file_service.delete_file(file_id, user['id'])
        
        if result['success']:
            return jsonify({'success': True})
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        print(f"Delete file error: {e}")
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


@file_bp.route('/files/<int:file_id>/image', methods=['GET'])
def get_image(file_id):
    """获取图片文件的二进制内容。

    用法:
    - 方法/路径: `GET /api/files/<file_id>/image`
    - 认证: Bearer Token
    - 成功响应: 图片二进制流（`image/*`）
    - 失败响应: 401 未登录；404 非图片或文件不存在；500 获取失败
    ---
    tags:
      - 文件
    summary: 获取图片文件内容
    description: 返回图片文件的二进制内容，需要登录验证
    produces:
      - image/*
    parameters:
      - in: path
        name: file_id
        type: integer
        required: true
        description: 文件ID
        example: 1
    responses:
      200:
        description: 图片文件
        schema:
          type: file
      401:
        description: 未登录
      404:
        description: 文件不存在、无权限或不是图片文件
      500:
        description: 服务器内部错误
    security:
      - bearerAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    db = get_session()
    try:
        file_obj = db.query(UploadedFile).filter(
            UploadedFile.id == file_id,
            UploadedFile.user_id == user['id']
        ).first()
        
        if not file_obj:
            return jsonify({'error': '文件不存在或无权限'}), 404
        
        # 检查是否为图片文件
        file_service = FileService()
        if not file_service.extractor.is_image(file_obj.file_extension):
            return jsonify({'error': '文件不是图片格式'}), 404
        
        # 检查文件是否存在
        if not os.path.exists(file_obj.file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 返回图片文件
        return send_file(
            file_obj.file_path,
            mimetype=file_obj.file_type or 'image/jpeg',
            as_attachment=False
        )
    except Exception as e:
        print(f"Get image error: {e}")
        return jsonify({'error': '获取图片失败'}), 500
    finally:
        db.close()


@file_bp.route('/files/supported', methods=['GET'])
def get_supported_extensions():
    """获取系统支持的文件扩展名与大小限制（公开接口）。

    用法:
    - 方法/路径: `GET /api/files/supported`
    - 认证: 无需登录
    - 成功响应: `{ "extensions": [...], "max_size_mb": 100 }`
    ---
    tags:
      - 文件
    summary: 获取支持的文件类型列表
    description: 返回系统支持上传的文件类型和大小限制
    produces:
      - application/json
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            extensions:
              type: array
              items:
                type: string
              description: 支持的文件扩展名列表
              example: ["pdf", "docx", "xlsx", "txt", "py", "js", "html", "css"]
            max_size_mb:
              type: integer
              description: 最大文件大小（MB）
              example: 100
        examples:
          application/json:
            extensions: ["pdf", "docx", "xlsx", "txt", "py", "js", "html", "css"]
            max_size_mb: 100
    """
    from ..services.file_service import FileExtractor
    extractor = FileExtractor()
    return jsonify({
        'extensions': extractor.get_supported_extensions(),
        'max_size_mb': 100
    })


