"""Initial schema — all tables for the Expense Portal.

Revision ID: 001
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- cost_centers ---
    op.create_table(
        "cost_centers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("budget_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("budget_period", sa.String(10), nullable=False, server_default=""),
        sa.Column("workday_id", sa.String(100), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- employees ---
    op.create_table(
        "employees",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("entra_oid", sa.String(100), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("manager_id", UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("cost_center_id", UUID(as_uuid=True), sa.ForeignKey("cost_centers.id"), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="employee"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("workday_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_employees_manager_id", "employees", ["manager_id"])
    op.create_index("ix_employees_cost_center_id", "employees", ["cost_center_id"])

    # --- expense_categories ---
    op.create_table(
        "expense_categories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("daily_limit", sa.Numeric(14, 2), nullable=True),
        sa.Column("is_reimbursable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- per_diem_rates ---
    op.create_table(
        "per_diem_rates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("expense_categories.id"), nullable=False),
        sa.Column("destination", sa.String(100), nullable=False),
        sa.Column("rate", sa.Numeric(14, 2), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- expense_reports ---
    op.create_table(
        "expense_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("report_number", sa.String(20), unique=True, nullable=False),
        sa.Column("submitter_id", UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("business_purpose", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("current_approver_id", UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("end_date >= start_date", name="ck_report_dates"),
    )
    op.create_index("ix_reports_submitter_status", "expense_reports", ["submitter_id", "status"])
    op.create_index("ix_reports_approver_status", "expense_reports", ["current_approver_id", "status"])
    op.create_index("ix_reports_submitted_at", "expense_reports", ["submitted_at"])
    op.create_index("ix_reports_status", "expense_reports", ["status"])

    # --- line_items ---
    op.create_table(
        "line_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", UUID(as_uuid=True), sa.ForeignKey("expense_reports.id"), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("expense_categories.id"), nullable=False),
        sa.Column("vendor_name", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("ocr_status", sa.String(20), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_line_items_report_sort", "line_items", ["report_id", "sort_order"])

    # --- receipts ---
    op.create_table(
        "receipts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("line_item_id", UUID(as_uuid=True), sa.ForeignKey("line_items.id"), unique=True, nullable=False),
        sa.Column("blob_path", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("ocr_task_id", sa.String(100), nullable=True),
        sa.Column("ocr_results", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- policy_violations ---
    op.create_table(
        "policy_violations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("line_item_id", UUID(as_uuid=True), sa.ForeignKey("line_items.id"), nullable=False),
        sa.Column("rule", sa.String(50), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- approval_actions (append-only audit trail) ---
    op.create_table(
        "approval_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", UUID(as_uuid=True), sa.ForeignKey("expense_reports.id"), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("ip_address", INET, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_approval_actions_report_id", "approval_actions", ["report_id"])

    # --- action_tokens ---
    op.create_table(
        "action_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", UUID(as_uuid=True), sa.ForeignKey("expense_reports.id"), nullable=False),
        sa.Column("approver_id", UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("intended_action", sa.String(20), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_action_tokens_token", "action_tokens", ["token"], unique=True)

    # --- approval_thresholds (singleton config) ---
    op.create_table(
        "approval_thresholds",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("finance_review_threshold", sa.Numeric(14, 2), nullable=False, server_default="500.00"),
        sa.Column("auto_escalation_business_days", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("reminder_business_days", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=True),
    )

    # --- notifications ---
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("recipient_id", UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("report_id", UUID(as_uuid=True), sa.ForeignKey("expense_reports.id"), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- workday_sync_logs ---
    op.create_table(
        "workday_sync_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("employees_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_centers_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_details", sa.Text(), nullable=True),
    )

    # Prevent UPDATE/DELETE on audit trail (SOX: NFR-015)
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'UPDATE and DELETE are not permitted on approval_actions';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_no_update_approval_actions
        BEFORE UPDATE OR DELETE ON approval_actions
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_no_update_approval_actions ON approval_actions;")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_mutation();")
    op.drop_table("workday_sync_logs")
    op.drop_table("notifications")
    op.drop_table("approval_thresholds")
    op.drop_table("action_tokens")
    op.drop_table("approval_actions")
    op.drop_table("policy_violations")
    op.drop_table("receipts")
    op.drop_table("line_items")
    op.drop_table("expense_reports")
    op.drop_table("per_diem_rates")
    op.drop_table("expense_categories")
    op.drop_table("employees")
    op.drop_table("cost_centers")
