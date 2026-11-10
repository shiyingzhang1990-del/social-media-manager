"""
Database models and session management.
"""
import hashlib
import secrets
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from backend.config import settings, DATA_DIR

import json

# ── Password Hashing Utilities ────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
    return f"pbkdf2:sha256:600000:{salt}:{dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        _, algo, iters, salt, stored = hashed.split(":")
        dk = hashlib.pbkdf2_hmac(algo, password.encode(), salt.encode(), int(iters))
        return dk.hex() == stored
    except (ValueError, AttributeError):
        return False


def generate_token() -> str:
    return secrets.token_hex(32)


engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── AccountGroup Model ────────────────────────────────────────────────
class AccountGroup(Base):
    __tablename__ = "account_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, default="")
    parent_id = Column(Integer, ForeignKey("account_groups.id"), nullable=True)
    color = Column(String(7), default="#3699ff")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    accounts = relationship("Account", back_populates="group")


# ── Account Model ─────────────────────────────────────────────────────
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("account_groups.id"), nullable=True)
    platform = Column(String(32), nullable=False, index=True)
    nickname = Column(String(128), default="")
    username = Column(String(128), default="")
    status = Column(String(16), default="active")                   # active, suspended, error
    credential_type = Column(String(16), default="cookie")          # cookie, password, qr, token
    credentials_encrypted = Column(Text, default="")                # Fernet-encrypted JSON
    tokens_encrypted = Column(Text, default="")
    meta_info = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    health_status = Column(String(16), default="unknown")           # healthy, warning, error, unknown
    health_check_at = Column(DateTime, nullable=True)
    health_details = Column(JSON, default=dict)
    platform_user_id = Column(String(128), default="")
    import_batch = Column(String(64), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_active_at = Column(DateTime, nullable=True)

    group = relationship("AccountGroup", back_populates="accounts")
    contents = relationship("Content", back_populates="account", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="account", cascade="all, delete-orphan")


# ── Content Model ─────────────────────────────────────────────────────
class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    platform = Column(String(32), nullable=False)
    content_type = Column(String(16), nullable=False)
    title = Column(String(256), default="")
    text = Column(Text, default="")
    media_paths = Column(JSON, default=list)
    media_ids = Column(JSON, default=list)                          # FK refs to MediaAsset
    tags = Column(JSON, default=list)
    extra = Column(JSON, default=dict)
    status = Column(String(16), default="draft")
    platform_post_id = Column(String(128), default="")
    error_message = Column(Text, default="")
    template_id = Column(Integer, ForeignKey("content_templates.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime, nullable=True)

    account = relationship("Account", back_populates="contents")
    schedules = relationship("Schedule", back_populates="content", cascade="all, delete-orphan")


# ── Schedule Model ────────────────────────────────────────────────────
class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False)
    platform = Column(String(32), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(String(16), default="pending")
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime, nullable=True)

    account = relationship("Account", back_populates="schedules")
    content = relationship("Content", back_populates="schedules")


# ── Publish Log Model ─────────────────────────────────────────────────
class PublishLog(Base):
    __tablename__ = "publish_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=True)
    platform = Column(String(32), nullable=False)
    action = Column(String(32), default="publish")
    status = Column(String(16), default="success")
    platform_response = Column(JSON, default=dict)
    error_message = Column(Text, default="")
    ip_used = Column(String(45), default="")
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── User Model ────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    token = Column(String(128), unique=True, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── MediaAsset Model ──────────────────────────────────────────────────
class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, default=0)
    mime_type = Column(String(64), default="")
    media_type = Column(String(16), nullable=False)                # image, video, audio
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    duration = Column(Float, default=0)
    thumbnail_path = Column(String(512), default="")
    tags = Column(JSON, default=list)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── ContentTemplate Model ─────────────────────────────────────────────
class ContentTemplate(Base):
    __tablename__ = "content_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    platform = Column(String(32), nullable=False)
    content_type = Column(String(16), default="text")
    title_template = Column(Text, default="")
    body_template = Column(Text, default="")
    hashtag_template = Column(Text, default="")
    media_placeholder_ids = Column(JSON, default=list)
    category = Column(String(64), default="")
    use_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── AnalyticsSnapshot Model ───────────────────────────────────────────
class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    platform = Column(String(32), nullable=False)
    snapshot_type = Column(String(16), nullable=False)              # daily, weekly, monthly
    snapshot_date = Column(DateTime, nullable=False)
    metrics = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_snapshot_unique", "account_id", "platform", "snapshot_type", "snapshot_date", unique=True),
    )


# ── LoginSession Model ────────────────────────────────────────────────
class LoginSession(Base):
    __tablename__ = "login_sessions"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(32), nullable=False)
    session_token = Column(String(128), unique=True, nullable=False, index=True)
    qr_url = Column(Text, default="")
    status = Column(String(16), default="pending")                  # pending, scanned, confirmed, expired, failed
    credential_data = Column(Text, default="")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── DB Init ───────────────────────────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_sync():
    return SessionLocal()


__all__ = ["Base", "Account", "AccountGroup", "Content", "Schedule", "PublishLog",
           "User", "MediaAsset", "ContentTemplate", "AnalyticsSnapshot", "LoginSession",
           "hash_password", "verify_password", "generate_token",
           "init_db", "get_db", "get_db_sync", "engine"]
