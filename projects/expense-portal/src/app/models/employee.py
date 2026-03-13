"""Employee and CostCenter ORM models — synced from Workday (FR-016)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class CostCenter(Base):
    __tablename__ = "cost_centers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    budget_period: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    workday_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    employees: Mapped[list["Employee"]] = relationship(back_populates="cost_center")


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        Index("ix_employees_manager_id", "manager_id"),
        Index("ix_employees_cost_center_id", "cost_center_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entra_oid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_centers.id"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="employee")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    workday_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    manager: Mapped["Employee | None"] = relationship(
        "Employee", remote_side="Employee.id", back_populates="direct_reports"
    )
    direct_reports: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="manager"
    )
    cost_center: Mapped["CostCenter | None"] = relationship(back_populates="employees")

    @property
    def is_manager(self) -> bool:
        return len(self.direct_reports) > 0

    @property
    def is_finance_reviewer(self) -> bool:
        return self.role in ("finance_reviewer", "finance_admin")

    @property
    def is_finance_admin(self) -> bool:
        return self.role == "finance_admin"
