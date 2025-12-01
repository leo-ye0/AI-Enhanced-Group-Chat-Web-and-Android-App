import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, func, Enum, select
from sqlalchemy.dialects.mysql import LONGTEXT
import enum
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+asyncmy://chatuser:chatpass@localhost:3306/groupchat")

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    messages = relationship("Message", back_populates="user")
    files = relationship("UploadedFile", back_populates="user")

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    content: Mapped[str] = mapped_column(Text())
    is_bot: Mapped[bool] = mapped_column(Boolean(), default=False)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="messages")

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_id: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text())
    file_data: Mapped[str] = mapped_column(LONGTEXT)
    summary: Mapped[str] = mapped_column(Text(), nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="files")

class TaskStatus(enum.Enum):
    pending = "pending"
    completed = "completed"

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text())
    extracted_from_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)
    assigned_to: Mapped[str] = mapped_column(Text(), nullable=True)
    due_date: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.pending)
    pending_assignment: Mapped[bool] = mapped_column(Boolean(), default=False)
    assignment_expires_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    datetime: Mapped[str] = mapped_column(String(100))
    duration_minutes: Mapped[int] = mapped_column()
    zoom_link: Mapped[str] = mapped_column(Text(), nullable=True)
    transcript_file_id: Mapped[int] = mapped_column(ForeignKey("uploaded_files.id", ondelete="SET NULL"), nullable=True)
    attendees: Mapped[str] = mapped_column(Text(), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

class DecisionOption(enum.Enum):
    A = "A"
    B = "B"
    C = "C"

class ProjectSettings(Base):
    """Project-wide settings"""
    __tablename__ = "project_settings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ship_date: Mapped[str] = mapped_column(String(100), nullable=True)
    updated_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Milestone(Base):
    """Project milestones for tracking progress"""
    __tablename__ = "milestones"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[str] = mapped_column(String(100))
    end_date: Mapped[str] = mapped_column(String(100))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Decision(Base):
    """Dialectic Engine: Decision Log for conflict resolutions"""
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conflict_id: Mapped[str] = mapped_column(String(255), index=True)
    triggering_conflict: Mapped[str] = mapped_column(Text())
    selected_option: Mapped[DecisionOption] = mapped_column(Enum(DecisionOption))
    reasoning: Mapped[str] = mapped_column(Text())
    decided_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

class DecisionCategory(enum.Enum):
    methodology = "Methodology"
    logistics = "Logistics"
    topic = "Topic"

class DecisionType(enum.Enum):
    locked = "locked"
    resolved = "resolved"
    consensus = "consensus"

class DecisionLog(Base):
    """Project Audit Trail: All team decisions with context"""
    __tablename__ = "decision_log"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    decision_text: Mapped[str] = mapped_column(String(500))
    rationale: Mapped[str] = mapped_column(Text())
    category: Mapped[DecisionCategory] = mapped_column(Enum(DecisionCategory))
    decision_type: Mapped[DecisionType] = mapped_column(Enum(DecisionType))
    created_by: Mapped[str] = mapped_column(String(100))  # User ID or "AI_Agent"
    chat_reference_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ConflictSeverity(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class ActiveConflict(Base):
    """Voting System: Active conflicts requiring team decision"""
    __tablename__ = "active_conflicts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conflict_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_statement: Mapped[str] = mapped_column(Text())
    conflicting_evidence: Mapped[str] = mapped_column(Text())
    source_file: Mapped[str] = mapped_column(String(255))
    severity: Mapped[ConflictSeverity] = mapped_column(Enum(ConflictSeverity))
    reason: Mapped[str] = mapped_column(Text())
    expires_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True))
    is_resolved: Mapped[bool] = mapped_column(Boolean(), default=False)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ConflictVote(Base):
    """Voting System: Individual votes on conflicts"""
    __tablename__ = "conflict_votes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conflict_id: Mapped[str] = mapped_column(String(255), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    selected_option: Mapped[DecisionOption] = mapped_column(Enum(DecisionOption))
    reasoning: Mapped[str] = mapped_column(Text())
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        # Ensure one vote per user per conflict
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'},
    )

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
