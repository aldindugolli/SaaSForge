import os

from flask import jsonify, request
from flask_login import current_user

from app.api.routes import api_bp
from app.knowledge.jobs import process_document_job
from app.knowledge.services import KnowledgeService
from app.services.api_platform import APIPermission, api_auth_required, require_api_permission
from app.services.base import NotFoundError, ValidationError


@api_bp.route("/knowledge/documents", methods=["GET"])
@api_auth_required
@require_api_permission(APIPermission.KNOWLEDGE_READ)
def api_knowledge_documents():
    org_id = request.args.get("organization_id") or (
        current_user.current_organization.id if hasattr(current_user, "current_organization") and current_user.current_organization else None
    )
    if not org_id:
        return jsonify({"error": "organization_id required"}), 400
    docs, total, total_pages = KnowledgeService.list_documents(
        org_id,
        collection_id=request.args.get("collection_id"),
        search=request.args.get("search"),
        type_filter=request.args.get("type"),
        page=request.args.get("page", 1, type=int),
    )
    return jsonify({
        "documents": [
            {
                "id": d.id,
                "name": d.name,
                "type": d.type,
                "size": d.size,
                "word_count": d.word_count,
                "chunk_count": d.chunk_count,
                "status": d.embedding_status,
                "tags": d.tags or [],
                "collection_id": d.collection_id,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
            }
            for d in docs
        ],
        "total": total,
        "page": request.args.get("page", 1, type=int),
        "total_pages": total_pages,
    })


@api_bp.route("/knowledge/documents", methods=["POST"])
@api_auth_required
@require_api_permission(APIPermission.KNOWLEDGE_WRITE)
def api_upload_document():
    org_id = request.form.get("organization_id") or (
        current_user.current_organization.id if hasattr(current_user, "current_organization") and current_user.current_organization else None
    )
    if not org_id:
        return jsonify({"error": "organization_id required"}), 400

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400

    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    if ext not in ("pdf", "docx", "txt", "md"):
        return jsonify({"error": "Unsupported file type"}), 400

    collection_id = request.form.get("collection_id") or None
    tags_raw = request.form.get("tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    user_id = current_user.id if hasattr(current_user, "id") else request.form.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    try:
        doc = KnowledgeService.upload_document(
            org_id=org_id,
            user_id=user_id,
            name=file.filename,
            file_data=file.read(),
            file_type=ext,
            collection_id=collection_id,
            tags=tags,
        )
        try:
            process_document_job.queue(doc.id)
        except Exception:
            KnowledgeService.process_document(doc.id)

        return jsonify({
            "id": doc.id,
            "name": doc.name,
            "type": doc.type,
            "size": doc.size,
            "status": doc.embedding_status,
            "created_at": doc.created_at.isoformat(),
        }), 201
    except (ValueError, ValidationError) as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/knowledge/documents/<doc_id>", methods=["GET"])
@api_auth_required
@require_api_permission(APIPermission.KNOWLEDGE_READ)
def api_get_document(doc_id):
    org_id = request.args.get("organization_id")
    if not org_id:
        return jsonify({"error": "organization_id required"}), 400
    doc = KnowledgeService.get_document(org_id, doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    return jsonify({
        "id": doc.id,
        "name": doc.name,
        "type": doc.type,
        "size": doc.size,
        "word_count": doc.word_count,
        "page_count": doc.page_count,
        "chunk_count": doc.chunk_count,
        "status": doc.embedding_status,
        "tags": doc.tags or [],
        "collection_id": doc.collection_id,
        "content_preview": (doc.content_text or "")[:2000],
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    })


@api_bp.route("/knowledge/documents/<doc_id>", methods=["DELETE"])
@api_auth_required
@require_api_permission(APIPermission.KNOWLEDGE_WRITE)
def api_delete_document(doc_id):
    org_id = request.args.get("organization_id")
    user_id = current_user.id if hasattr(current_user, "id") else request.args.get("user_id")
    if not org_id or not user_id:
        return jsonify({"error": "organization_id and user_id required"}), 400
    try:
        KnowledgeService.delete_document(org_id, doc_id, user_id)
        return jsonify({"status": "deleted"}), 200
    except NotFoundError:
        return jsonify({"error": "Document not found"}), 404


@api_bp.route("/knowledge/collections", methods=["GET"])
@api_auth_required
@require_api_permission(APIPermission.KNOWLEDGE_READ)
def api_knowledge_collections():
    org_id = request.args.get("organization_id")
    if not org_id:
        return jsonify({"error": "organization_id required"}), 400
    collections = KnowledgeService.list_collections(org_id)
    return jsonify({
        "collections": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "document_count": c.document_count,
                "created_at": c.created_at.isoformat(),
            }
            for c in collections
        ]
    })


@api_bp.route("/knowledge/collections", methods=["POST"])
@api_auth_required
@require_api_permission(APIPermission.KNOWLEDGE_WRITE)
def api_create_collection():
    data = request.json or {}
    org_id = data.get("organization_id")
    user_id = current_user.id if hasattr(current_user, "id") else data.get("user_id")
    name = data.get("name", "").strip()
    description = data.get("description", "").strip() or None
    if not org_id or not user_id or not name:
        return jsonify({"error": "organization_id, user_id, and name required"}), 400
    try:
        collection = KnowledgeService.create_collection(org_id, user_id, name, description)
        return jsonify({
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "created_at": collection.created_at.isoformat(),
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/knowledge/search", methods=["GET"])
@api_auth_required
@require_api_permission(APIPermission.KNOWLEDGE_READ)
def api_knowledge_search():
    org_id = request.args.get("organization_id")
    query = request.args.get("q", "").strip()
    if not org_id or not query:
        return jsonify({"error": "organization_id and q required"}), 400
    collection_id = request.args.get("collection_id")
    limit = request.args.get("limit", 10, type=int)
    results = KnowledgeService.search(
        org_id, query, collection_id=collection_id, limit=limit
    )
    return jsonify({"results": results, "query": query})


@api_bp.route("/knowledge/chat", methods=["POST"])
@api_auth_required
@require_api_permission(APIPermission.KNOWLEDGE_WRITE)
def api_create_chat():
    data = request.json or {}
    org_id = data.get("organization_id")
    user_id = current_user.id if hasattr(current_user, "id") else data.get("user_id")
    title = data.get("title", "API Conversation").strip()
    document_id = data.get("document_id")
    if not org_id or not user_id:
        return jsonify({"error": "organization_id and user_id required"}), 400
    conversation = KnowledgeService.create_conversation(
        org_id, user_id, title, document_id=document_id
    )
    return jsonify({
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
    }), 201


@api_bp.route("/knowledge/chat/<conversation_id>/messages", methods=["GET"])
@api_auth_required
@require_api_permission(APIPermission.KNOWLEDGE_READ)
def api_chat_messages(conversation_id):
    messages = KnowledgeService.get_conversation_messages(conversation_id)
    return jsonify({
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
    })


@api_bp.route("/knowledge/chat/<conversation_id>/send", methods=["POST"])
@api_auth_required
@require_api_permission(APIPermission.KNOWLEDGE_WRITE)
def api_send_message(conversation_id):
    data = request.json or {}
    org_id = data.get("organization_id")
    user_id = current_user.id if hasattr(current_user, "id") else data.get("user_id")
    content = data.get("message", "").strip()
    if not org_id or not user_id or not content:
        return jsonify({"error": "organization_id, user_id, and message required"}), 400
    try:
        user_msg, assistant_msg = KnowledgeService.send_message(
            org_id, conversation_id, user_id, content
        )
        return jsonify({
            "user_message": {
                "id": user_msg.id,
                "content": user_msg.content,
                "created_at": user_msg.created_at.isoformat(),
            },
            "assistant_message": {
                "id": assistant_msg.id,
                "content": assistant_msg.content,
                "citations": assistant_msg.citations,
                "created_at": assistant_msg.created_at.isoformat(),
            },
        }), 201
    except NotFoundError:
        return jsonify({"error": "Conversation not found"}), 404
