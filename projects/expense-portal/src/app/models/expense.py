"""ExpenseReport, LineItem, and Receipt ORM models."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base

REPORT_STATUSES = (
    "draft",
    "submitted",
    "manager_approved",
    "finance_review",
    "approved",
    "rejected",
    "information_requested",
    "payment_processing",
    "paid",
    "cancelled",
)


class ExpenseReport(Base):
    __tablename__ = "expense_reports"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_report_dates"),
        CheckConstraint(
            f"status IN ({','.join(repr(s) for s in REPORT_STATUSES)})",
            name="ck_report_status",
        ),
        Index("ix_reports_submitter_status", "submitter_id", "status"),
        Index("ix_reports_approver_status", "current_approver_id", "status"),
        Index("ix_reports_submitted_at", "submitted_at"),
        Index("ix_reports_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    submitter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    business_purpose: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    current_approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    submitter: Mapped["Employee"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Employee", foreign_keys=[submitter_id]
    )
    current_approver: Mapped["Employee | None"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Employee", foreign_keys=[current_approver_id]
    )
    line_items: Mapped[list["LineItem"]] = relationship(
        back_populates="report", order_by="LineItem.sort_order"
    )
    approval_actions: Mapped[list["ApprovalAction"]] = relationship(  # type: ignore[name-defined] # noqa: F821
        back_populates="report", order_by="ApprovalAction.created_at"
    )

    @property
    def is_editable(self) -> bool:
        return self.status in ("draft", "rejected")

    @property
    def line_item_count(self) -> int:
        return len(self.line_items)


class LineItem(Base):
    __tablename__ = "line_items"
    __table_args__ = (Index("ix_line_items_report_sort", "report_id", "sort_order"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expense_reports.id"), nullable=False
    )
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expense_categories.id"), nullable=False
    )
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    ocr_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    report: Mapped["ExpenseReport"] = relationship(back_populates="line_items")
    category: Mapped["ExpenseCategory"] = relationship()  # type: ignore[name-defined] # noqa: F821
    receipt: Mapped["Receipt | None"] = relationship(back_populates="line_item", uselist=False)
    policy_violations: Mapped[list["PolicyViolation"]] = relationship(back_populates="line_item")


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("line_items.id"), unique=True, nullable=False
    )
    blob_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    ocr_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ocr_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    line_item: Mapped["LineItem"] = relationship(back_populates="receipt")


class PolicyViolation(Base):
    __tablename__ = "policy_violations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("line_items.id"), nullable=False
    )
    rule: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    is_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    line_item: Mapped["LineItem"] = relationship(back_populates="policy_violations")
