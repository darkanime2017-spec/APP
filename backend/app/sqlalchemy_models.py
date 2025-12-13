"""
SQLAlchemy ORM models for the application.

This module defines the database table structures as Python classes using SQLAlchemy's
Declarative Mapping. These models are used by CRUD operations to interact with the
PostgreSQL database.
"""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BIGINT,
    INT,
    TIMESTAMP,
    BigInteger,
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class UserRole(enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class Tps(Base):
    __tablename__ = "tps"
    tp_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    grace_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="15")
    max_access_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default="4")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    surname: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False, server_default="student")
    firebase_uid: Mapped[str | None] = mapped_column(Text, index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    has_submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class AssignedClass(Base):
    __tablename__ = "assigned_classes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tp_id: Mapped[int] = mapped_column(ForeignKey("tps.tp_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    class_1: Mapped[str] = mapped_column(Text, nullable=False)
    class_2: Mapped[str] = mapped_column(Text, nullable=False)
    class_3: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("tp_id", "user_id", name="uq_assigned_classes_tp_user"),)


class HiddenTestId(Base):
    __tablename__ = "hidden_test_ids"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tp_id: Mapped[int] = mapped_column(ForeignKey("tps.tp_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    text_id: Mapped[str] = mapped_column(Text, nullable=False)
    ground_truth: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("tp_id", "user_id", "text_id", name="uq_hidden_test_ids_tp_user_text"),)


class File(Base):
    __tablename__ = "files"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tp_id: Mapped[int | None] = mapped_column(ForeignKey("tps.tp_id", ondelete="SET NULL"))
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    drive_file_id: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    original_filename: Mapped[str | None] = mapped_column(Text)
    stored_filename: Mapped[str | None] = mapped_column(Text)
    file_type: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    uploaded_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tp_id: Mapped[int] = mapped_column(ForeignKey("tps.tp_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_id: Mapped[UUID] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    file_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="uploaded")
    server_timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class ActivityLog(Base):
    __tablename__ = "activity_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    tp_id: Mapped[int | None] = mapped_column(ForeignKey("tps.tp_id", ondelete="SET NULL"))
    action_key: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class ResultsSummary(Base):
    __tablename__ = "results_summary"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tp_id: Mapped[int] = mapped_column(ForeignKey("tps.tp_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Numeric(5, 4))
    f1_macro: Mapped[float | None] = mapped_column(Numeric(5, 4))
    evaluated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    details: Mapped[dict | None] = mapped_column(JSONB)
