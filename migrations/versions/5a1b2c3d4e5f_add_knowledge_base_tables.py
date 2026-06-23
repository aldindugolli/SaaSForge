"""Add knowledge base tables (collections, documents, chunks, conversations, messages, usage)

Revision ID: 5a1b2c3d4e5f
Revises: 4b2c3d4e5f6a
Create Date: 2025-06-23 10:00:00.000000

"""
from datetime import UTC, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5a1b2c3d4e5f"
down_revision: Union[str, None] = "4b2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # knowledge_collections
    op.create_table(
        "knowledge_collections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(50), server_default="folder"),
        sa.Column("document_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # knowledge_documents
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("collection_id", sa.String(36), sa.ForeignKey("knowledge_collections.id"), nullable=True, index=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("uploaded_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("page_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("chunk_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("embedding_status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("search_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # knowledge_document_chunks
    op.create_table(
        "knowledge_document_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("knowledge_documents.id"), nullable=False, index=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_chunk_document_index", "knowledge_document_chunks", ["document_id", "chunk_index"])

    # knowledge_conversations
    op.create_table(
        "knowledge_conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("knowledge_documents.id"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # knowledge_messages
    op.create_table(
        "knowledge_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("knowledge_conversations.id"), nullable=False, index=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # knowledge_usage
    op.create_table(
        "knowledge_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("documents_uploaded", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("searches_performed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("chat_messages", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ai_tokens_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("active_users", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_unique_constraint("uq_knowledge_usage_org_date", "knowledge_usage", ["organization_id", "date"])


def downgrade():
    op.drop_table("knowledge_usage")
    op.drop_table("knowledge_messages")
    op.drop_table("knowledge_conversations")
    op.drop_index("idx_chunk_document_index", table_name="knowledge_document_chunks")
    op.drop_table("knowledge_document_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("knowledge_collections")
