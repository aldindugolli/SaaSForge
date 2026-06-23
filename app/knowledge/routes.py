import os

from flask import (
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.core.extensions import db
from app.knowledge import knowledge_bp
from app.knowledge.jobs import process_document_job
from app.knowledge.models import (
    KnowledgeCollection,
    KnowledgeConversation,
    KnowledgeDocument,
)
from app.knowledge.services import KnowledgeService
from app.services.base import NotFoundError, ValidationError
from app.services.decorators import org_required


@knowledge_bp.before_request
@login_required
def require_login():
    pass


@knowledge_bp.route("/")
@org_required
def dashboard():
    org = current_user.current_organization
    stats = KnowledgeService.get_dashboard_stats(org.id)
    return render_template("knowledge/dashboard.html", **stats)


@knowledge_bp.route("/documents")
@org_required
def documents():
    org = current_user.current_organization
    page = request.args.get("page", 1, type=int)
    collection_id = request.args.get("collection_id")
    search = request.args.get("search")
    tag = request.args.get("tag")
    type_filter = request.args.get("type")
    docs, total, total_pages = KnowledgeService.list_documents(
        org.id,
        collection_id=collection_id,
        search=search,
        tag=tag,
        type_filter=type_filter,
        page=page,
    )
    collections = KnowledgeService.list_collections(org.id)
    return render_template(
        "knowledge/documents.html",
        documents=docs,
        page=page,
        total_pages=total_pages,
        total=total,
        collections=collections,
        current_collection=collection_id,
        search_query=search,
        type_filter=type_filter,
    )


@knowledge_bp.route("/documents/upload", methods=["GET", "POST"])
@org_required
def upload():
    org = current_user.current_organization
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("No file selected.", "error")
            return redirect(url_for("knowledge.upload"))

        ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
        if ext not in ("pdf", "docx", "txt", "md"):
            flash("Unsupported file type. Allowed: PDF, DOCX, TXT, MD", "error")
            return redirect(url_for("knowledge.upload"))

        collection_id = request.form.get("collection_id") or None
        tags_raw = request.form.get("tags", "")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        try:
            doc = KnowledgeService.upload_document(
                org_id=org.id,
                user_id=current_user.id,
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

            flash(f"Document '{file.filename}' uploaded successfully.", "success")
            return redirect(url_for("knowledge.documents"))
        except (ValueError, ValidationError) as e:
            flash(str(e), "error")
            return redirect(url_for("knowledge.upload"))

    collections = KnowledgeService.list_collections(org.id)
    return render_template("knowledge/upload.html", collections=collections)


@knowledge_bp.route("/documents/<doc_id>")
@org_required
def document_detail(doc_id):
    org = current_user.current_organization
    doc = KnowledgeService.get_document(org.id, doc_id)
    if not doc:
        flash("Document not found.", "error")
        return redirect(url_for("knowledge.documents"))
    collections = KnowledgeService.list_collections(org.id)
    conversations = KnowledgeConversation.query.filter_by(
        document_id=doc_id, organization_id=org.id
    ).order_by(KnowledgeConversation.updated_at.desc()).limit(10).all()
    return render_template(
        "knowledge/document_detail.html",
        doc=doc,
        collections=collections,
        conversations=conversations,
    )


@knowledge_bp.route("/documents/<doc_id>/edit", methods=["POST"])
@org_required
def edit_document(doc_id):
    org = current_user.current_organization
    name = request.form.get("name")
    collection_id = request.form.get("collection_id") or None
    tags_raw = request.form.get("tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None
    try:
        KnowledgeService.update_document(
            org.id, doc_id, current_user.id, name=name, collection_id=collection_id, tags=tags
        )
        flash("Document updated.", "success")
    except NotFoundError as e:
        flash(str(e), "error")
    return redirect(url_for("knowledge.document_detail", doc_id=doc_id))


@knowledge_bp.route("/documents/<doc_id>/reprocess", methods=["POST"])
@org_required
def reprocess_document(doc_id):
    org = current_user.current_organization
    doc = KnowledgeService.get_document(org.id, doc_id)
    if not doc:
        flash("Document not found.", "error")
        return redirect(url_for("knowledge.documents"))
    doc.embedding_status = "pending"
    db.session.commit()
    try:
        process_document_job.queue(doc.id)
        flash("Document reprocessing started.", "success")
    except Exception:
        KnowledgeService.process_document(doc.id)
        flash("Document reprocessed.", "success")
    return redirect(url_for("knowledge.document_detail", doc_id=doc_id))


@knowledge_bp.route("/documents/<doc_id>/delete", methods=["POST"])
@org_required
def delete_document(doc_id):
    org = current_user.current_organization
    try:
        KnowledgeService.delete_document(org.id, doc_id, current_user.id)
        flash("Document deleted.", "success")
    except NotFoundError as e:
        flash(str(e), "error")
    return redirect(url_for("knowledge.documents"))


@knowledge_bp.route("/collections")
@org_required
def collections():
    org = current_user.current_organization
    cols = KnowledgeService.list_collections(org.id)
    return render_template("knowledge/collections.html", collections=cols)


@knowledge_bp.route("/collections/create", methods=["POST"])
@org_required
def create_collection():
    org = current_user.current_organization
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip() or None
    if not name:
        flash("Collection name is required.", "error")
        return redirect(url_for("knowledge.collections"))
    try:
        KnowledgeService.create_collection(org.id, current_user.id, name, description)
        flash(f"Collection '{name}' created.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("knowledge.collections"))


@knowledge_bp.route("/collections/<collection_id>/delete", methods=["POST"])
@org_required
def delete_collection(collection_id):
    org = current_user.current_organization
    try:
        KnowledgeService.delete_collection(org.id, collection_id, current_user.id)
        flash("Collection deleted.", "success")
    except NotFoundError as e:
        flash(str(e), "error")
    return redirect(url_for("knowledge.collections"))


@knowledge_bp.route("/search")
@org_required
def search():
    org = current_user.current_organization
    query = request.args.get("q", "").strip()
    collection_id = request.args.get("collection_id")
    use_semantic = request.args.get("mode", "hybrid") != "text"
    results = []
    if query:
        results = KnowledgeService.search(
            org.id, query, collection_id=collection_id, use_semantic=use_semantic
        )
    collections = KnowledgeService.list_collections(org.id)
    return render_template(
        "knowledge/search.html",
        query=query,
        results=results,
        collections=collections,
        current_collection=collection_id,
        mode="semantic" if use_semantic else "text",
    )


@knowledge_bp.route("/chat")
@org_required
def chat():
    org = current_user.current_organization
    page = request.args.get("page", 1, type=int)
    conversations, total, total_pages = KnowledgeService.list_conversations(
        org.id, page=page
    )
    return render_template(
        "knowledge/chat.html",
        conversations=conversations,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@knowledge_bp.route("/chat/new", methods=["GET", "POST"])
@org_required
def new_chat():
    org = current_user.current_organization
    if request.method == "POST":
        title = request.form.get("title", "New Conversation").strip()
        document_id = request.form.get("document_id") or None
        conversation = KnowledgeService.create_conversation(
            org.id, current_user.id, title, document_id=document_id
        )
        return redirect(url_for("knowledge.view_chat", conversation_id=conversation.id))
    documents = KnowledgeDocument.query.filter_by(
        organization_id=org.id
    ).order_by(KnowledgeDocument.created_at.desc()).limit(50).all()
    return render_template("knowledge/new_chat.html", documents=documents)


@knowledge_bp.route("/chat/<conversation_id>")
@org_required
def view_chat(conversation_id):
    org = current_user.current_organization
    conversation = KnowledgeService.get_conversation(org.id, conversation_id)
    if not conversation:
        flash("Conversation not found.", "error")
        return redirect(url_for("knowledge.chat"))
    messages = KnowledgeService.get_conversation_messages(conversation_id)
    return render_template(
        "knowledge/view_chat.html",
        conversation=conversation,
        messages=messages,
    )


@knowledge_bp.route("/chat/<conversation_id>/send", methods=["POST"])
@org_required
def send_message(conversation_id):
    org = current_user.current_organization
    content = request.form.get("message", "").strip()
    if not content:
        flash("Message cannot be empty.", "error")
        return redirect(url_for("knowledge.view_chat", conversation_id=conversation_id))
    try:
        KnowledgeService.send_message(org.id, conversation_id, current_user.id, content)
    except NotFoundError:
        flash("Conversation not found.", "error")
        return redirect(url_for("knowledge.chat"))
    return redirect(url_for("knowledge.view_chat", conversation_id=conversation_id))


@knowledge_bp.route("/chat/<conversation_id>/delete", methods=["POST"])
@org_required
def delete_conversation(conversation_id):
    org = current_user.current_organization
    try:
        KnowledgeService.delete_conversation(org.id, conversation_id, current_user.id)
        flash("Conversation deleted.", "success")
    except NotFoundError:
        flash("Conversation not found.", "error")
    return redirect(url_for("knowledge.chat"))


@knowledge_bp.route("/analytics")
@org_required
def analytics():
    org = current_user.current_organization
    usage = KnowledgeService.get_usage_stats(org.id)
    chart_data = KnowledgeService.get_usage_analytics(org.id)
    return render_template(
        "knowledge/analytics.html",
        usage=usage,
        chart_data=chart_data,
    )


@knowledge_bp.route("/api/documents")
@org_required
def api_documents():
    org = current_user.current_organization
    docs, total, total_pages = KnowledgeService.list_documents(
        org.id,
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
                "status": d.embedding_status,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ],
        "total": total,
        "page": request.args.get("page", 1, type=int),
        "total_pages": total_pages,
    })


@knowledge_bp.route("/api/stats")
@org_required
def api_stats():
    org = current_user.current_organization
    return jsonify(KnowledgeService.get_dashboard_stats(org.id))
