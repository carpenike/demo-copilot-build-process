"""Pydantic request/response schemas for the REST API (NFR-020, NFR-023)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# --- Shared ---


class PaginatedResponse(BaseModel):
    """Cursor-based pagination wrapper (NFR-022)."""

    next_cursor: str | None = None
    total: int = 0


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details error response (NFR-023)."""

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None


# --- Employee / CostCenter ---


class CostCenterBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str


class EmployeeBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str = Field(validation_alias="full_name")
    cost_center: str | None = None


class SubmitterDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str = Field(validation_alias="full_name")
    cost_center: str | None = None
    cost_center_id: uuid.UUID | None = None


# --- Policy Violation ---


class PolicyViolationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_item_id: uuid.UUID
    rule: str
    message: str
    blocking: bool = Field(validation_alias="is_blocking")


# --- Line Item ---


class LineItemCreate(BaseModel):
    date: date = Field(alias="date")
    category: str
    vendor_name: str = Field(max_length=255)
    amount: Decimal = Field(gt=0)
    currency: str = Field(pattern=r"^(USD|CAD)$")
    description: str = Field(max_length=500)


class LineItemUpdate(BaseModel):
    date: date | None = None
    category: str | None = None
    vendor_name: str | None = Field(default=None, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, pattern=r"^(USD|CAD)$")
    description: str | None = Field(default=None, max_length=500)


class LineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: date = Field(validation_alias="expense_date")
    category: str
    vendor_name: str
    amount: Decimal
    currency: str
    description: str
    receipt_url: str | None = None
    policy_violations: list[PolicyViolationOut] = []
    ocr_status: str | None = None
    created_at: datetime


# --- Receipt ---


class ReceiptUploadOut(BaseModel):
    receipt_url: str
    ocr_status: str = "processing"
    ocr_task_id: str


class OcrStatusOut(BaseModel):
    task_id: str
    status: str
    extracted_fields: dict | None = None


# --- Expense Report ---


class ReportCreate(BaseModel):
    title: str = Field(max_length=255)
    start_date: date
    end_date: date
    business_purpose: str = Field(max_length=1000)
    submit: bool = False


class ReportUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    business_purpose: str | None = Field(default=None, max_length=1000)


class ReportSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: str
    start_date: date
    end_date: date
    business_purpose: str
    total_amount: Decimal
    currency: str
    line_item_count: int
    submitted_at: datetime | None = None
    submitter: EmployeeBrief | None = None
    created_at: datetime
    updated_at: datetime


class ReportListOut(PaginatedResponse):
    data: list[ReportSummaryOut]


class ApprovalHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action: str
    actor: str
    timestamp: datetime = Field(validation_alias="created_at")
    comment: str | None = None


class PolicyViolationsSummary(BaseModel):
    blocking: int = 0
    warnings: int = 0


class ReportDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: str
    start_date: date
    end_date: date
    business_purpose: str
    total_amount: Decimal
    currency: str
    submitter: SubmitterDetail | None = None
    line_items: list[LineItemOut] = []
    approval_history: list[ApprovalHistoryEntry] = []
    policy_violations_summary: PolicyViolationsSummary | None = None
    created_at: datetime
    updated_at: datetime


class SubmitRequest(BaseModel):
    acknowledge_warnings: bool = False


class SubmitResponse(BaseModel):
    id: uuid.UUID
    status: str = "submitted"
    submitted_at: datetime
    routed_to: EmployeeBrief | None = None


# --- Approvals ---


class PendingApprovalOut(BaseModel):
    report_id: uuid.UUID
    title: str
    submitter: EmployeeBrief
    total_amount: Decimal
    line_item_count: int
    submitted_at: datetime
    pending_since: datetime
    approval_type: str


class PendingApprovalListOut(PaginatedResponse):
    data: list[PendingApprovalOut]


class ApproveRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=500)


class RejectRequest(BaseModel):
    reason: str = Field(max_length=1000)


class RequestInfoRequest(BaseModel):
    question: str = Field(max_length=1000)


class ApprovalResponse(BaseModel):
    report_id: uuid.UUID
    new_status: str
    next_step: str | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    requested_at: datetime | None = None


# --- Dashboard / Reports ---


class FinanceSummary(BaseModel):
    total_amount: Decimal
    report_count: int
    average_amount: Decimal
    period: str


class CostCenterBreakdown(BaseModel):
    cost_center: str
    total: Decimal
    count: int


class CategoryBreakdown(BaseModel):
    category: str
    total: Decimal
    count: int


class StatusBreakdown(BaseModel):
    status: str
    total: Decimal
    count: int


class FinanceReportOut(BaseModel):
    summary: FinanceSummary
    by_cost_center: list[CostCenterBreakdown] = []
    by_category: list[CategoryBreakdown] = []
    by_status: list[StatusBreakdown] = []


class EmployeeSpendOut(BaseModel):
    employee: EmployeeBrief
    submitted: Decimal
    approved: Decimal
    pending: Decimal


class ManagerReportOut(BaseModel):
    cost_center: str
    budget: Decimal
    period: str
    total_submitted: Decimal
    total_approved: Decimal
    remaining_budget: Decimal
    by_employee: list[EmployeeSpendOut] = []


# --- Admin ---


class PerDiemRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    destination: str
    rate: Decimal


class PerDiemRateCreate(BaseModel):
    destination: str = Field(max_length=100)
    rate: Decimal = Field(gt=0)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    daily_limit: Decimal | None = None
    reimbursable: bool = Field(validation_alias="is_reimbursable")
    per_diem_rates: list[PerDiemRateOut] = []


class CategoryCreate(BaseModel):
    name: str = Field(max_length=100)
    daily_limit: Decimal | None = None
    reimbursable: bool = True
    per_diem_rates: list[PerDiemRateCreate] = []


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    daily_limit: Decimal | None = None
    reimbursable: bool | None = None
    per_diem_rates: list[PerDiemRateCreate] | None = None


class ThresholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finance_review_threshold: Decimal
    auto_escalation_days: int = Field(validation_alias="auto_escalation_business_days")
    reminder_days: int = Field(validation_alias="reminder_business_days")


class ThresholdUpdate(BaseModel):
    finance_review_threshold: Decimal | None = None
    auto_escalation_days: int | None = None
    reminder_days: int | None = None


# --- Health ---


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]
