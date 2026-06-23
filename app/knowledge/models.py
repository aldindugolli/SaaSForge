from datetime import UTC, datetime
from uuid import uuid4

from app.core.extensions import db


def gen_uuid():
    return str(uuid4())


def utcnow():
    return datetime.now(UTC)


class KnowledgeCollection(db.Model):
    __tablename__ = "knowledge_collections"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), default="folder")
    document_count = db.Column(db.Integer, default=0, nullable=False)
    created_by_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    organization = db.relationship("Organization", backref="knowledge_collections")
    created_by = db.relationship("User", backref="created_collections")
    documents = db.relationship(
        "KnowledgeDocument",
        back_populates="collection",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<KnowledgeCollection {self.name}>"


class KnowledgeDocument(db.Model):
    __tablename__ = "knowledge_documents"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    collection_id = db.Column(
        db.String(36), db.ForeignKey("knowledge_collections.id"), nullable=True, index=True
    )
    name = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    content_text = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    tags = db.Column(db.JSON, nullable=True)
    uploaded_by_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), nullable=False
    )
    word_count = db.Column(db.Integer, nullable=True, default=0)
    page_count = db.Column(db.Integer, nullable=True, default=0)
    chunk_count = db.Column(db.Integer, nullable=True, default=0)
    embedding_status = db.Column(
        db.String(20), nullable=False, default="pending"
    )
    search_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    organization = db.relationship("Organization", backref="knowledge_documents")
    collection = db.relationship(
        "KnowledgeCollection", back_populates="documents"
    )
    uploaded_by = db.relationship("User", backref="uploaded_documents")
    chunks = db.relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    conversations = db.relationship(
        "KnowledgeConversation",
        back_populates="document",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<KnowledgeDocument {self.name}>"


class DocumentChunk(db.Model):
    __tablename__ = "knowledge_document_chunks"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    document_id = db.Column(
        db.String(36), db.ForeignKey("knowledge_documents.id"), nullable=False, index=True
    )
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.JSON, nullable=True)
    token_count = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    document = db.relationship("KnowledgeDocument", back_populates="chunks")

    __table_args__ = (
        db.Index("idx_chunk_document_index", "document_id", "chunk_index"),
    )

    def __repr__(self):
        return f"<DocumentChunk {self.document_id} [{self.chunk_index}]>"


class KnowledgeConversation(db.Model):
    __tablename__ = "knowledge_conversations"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    document_id = db.Column(
        db.String(36), db.ForeignKey("knowledge_documents.id"), nullable=True
    )
    title = db.Column(db.String(500), nullable=False)
    message_count = db.Column(db.Integer, nullable=False, default=0)
    created_by_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    organization = db.relationship("Organization", backref="knowledge_conversations")
    document = db.relationship("KnowledgeDocument", back_populates="conversations")
    created_by = db.relationship("User", backref="knowledge_conversations")
    messages = db.relationship(
        "KnowledgeMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="KnowledgeMessage.created_at",
    )

    def __repr__(self):
        return f"<KnowledgeConversation {self.title}>"


class KnowledgeMessage(db.Model):
    __tablename__ = "knowledge_messages"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    conversation_id = db.Column(
        db.String(36), db.ForeignKey("knowledge_conversations.id"), nullable=False, index=True
    )
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    citations = db.Column(db.JSON, nullable=True)
    token_count = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    conversation = db.relationship(
        "KnowledgeConversation", back_populates="messages"
    )

    def __repr__(self):
        return f"<KnowledgeMessage {self.role}>"


class KnowledgeUsage(db.Model):
    __tablename__ = "knowledge_usage"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    date = db.Column(db.Date, nullable=False)
    documents_uploaded = db.Column(db.Integer, nullable=False, default=0)
    searches_performed = db.Column(db.Integer, nullable=False, default=0)
    chat_messages = db.Column(db.Integer, nullable=False, default=0)
    ai_tokens_used = db.Column(db.Integer, nullable=False, default=0)
    active_users = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    organization = db.relationship("Organization", backref="knowledge_usage")

    __table_args__ = (
        db.UniqueConstraint(
            "organization_id", "date", name="uq_knowledge_usage_org_date"
        ),
    )

    def __repr__(self):
        return f"<KnowledgeUsage {self.organization_id} {self.date}>"
