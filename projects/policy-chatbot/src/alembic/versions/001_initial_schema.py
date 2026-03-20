"""001 — initial schema: all 10 entities from data-model.md.

Revision ID: 001
Revises:
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("department", sa.String(100)),
        sa.Column("location", sa.String(200)),
        sa.Column("role", sa.String(20), nullable=False, server_default="Employee"),
        sa.Column("manager_email", sa.String(320)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), unique=True, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("review_date", sa.Date),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("current_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("page_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # --- document_versions ---
    op.create_table(
        "document_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("blob_path", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("uploaded_by", sa.String(320), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("last_message_at", sa.DateTime(timezone=True)),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("escalation_ticket_id", sa.String(100)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=False
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("citations", JSONB),
        sa.Column("intent", JSONB),
        sa.Column("response_type", sa.String(50)),
        sa.Column("checklist", JSONB),
        sa.Column("wayfinding", JSONB),
        sa.Column("token_count", sa.Integer),
        sa.Column("response_time_ms", sa.Float),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # --- feedback ---
    op.create_table(
        "feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("messages.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rating", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_unique_constraint("uq_feedback_message_id", "feedback", ["message_id"])

    # --- flagged_topics ---
    op.create_table(
        "flagged_topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("negative_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sample_comments", JSONB),
        sa.Column(
            "first_flagged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # --- analytics_daily ---
    op.create_table(
        "analytics_daily",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("date", sa.Date, unique=True, nullable=False),
        sa.Column("total_queries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("resolved_queries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("escalated_queries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("no_match_queries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("positive_feedback_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("negative_feedback_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_response_time_ms", sa.Float, nullable=False, server_default="0"),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # --- intent_counts ---
    op.create_table(
        "intent_counts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("intent_label", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("count", sa.Integer, nullable=False, server_default="0"),
    )

    # --- unanswered_queries ---
    op.create_table(
        "unanswered_queries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("detected_intent", sa.String(200)),
        sa.Column("detected_domain", sa.String(50)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("unanswered_queries")
    op.drop_table("intent_counts")
    op.drop_table("analytics_daily")
    op.drop_table("flagged_topics")
    op.drop_constraint("uq_feedback_message_id", "feedback", type_="unique")
    op.drop_table("feedback")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_table("users")
