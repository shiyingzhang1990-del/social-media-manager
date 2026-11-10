"""
Content management and publishing API routes.
"""
from datetime import datetime, timezone
import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db, get_db_sync, Account, Content, Schedule, PublishLog, MediaAsset
from backend.platforms import get_platform
from backend.config import CONTENT_DIR
import uuid
import os
import shutil

router = APIRouter(prefix="/api/content", tags=["content"])


class ContentCreate(BaseModel):
    account_id: int
    content_type: str = "text"
    title: str = ""
    text: str = ""
    tags: list[str] = []
    extra: dict[str, Any] = {}
    schedule_at: str | None = None  # ISO datetime


class ContentUpdate(BaseModel):
    title: str | None = None
    text: str | None = None
    tags: list[str] | None = None
    extra: dict[str, Any] | None = None


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a media file, save to disk and MediaAsset table."""
    ext = os.path.splitext(file.filename or "file")[1] or ".bin"
    file_id = str(uuid.uuid4())
    save_name = f"{file_id}{ext}"
    save_path = CONTENT_DIR / save_name

    content_bytes = await file.read()
    with open(save_path, "wb") as f:
        f.write(content_bytes)

    # Determine media type
    mime = file.content_type or ""
    if mime.startswith("image/"):
        media_type = "image"
    elif mime.startswith("video/"):
        media_type = "video"
    elif mime.startswith("audio/"):
        media_type = "audio"
    else:
        media_type = "image" if ext.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"] else "video" if ext.lower() in [".mp4", ".mov", ".avi"] else "image"

    db = get_db_sync()
    try:
        asset = MediaAsset(
            filename=file.filename or save_name,
            file_path=str(save_path),
            file_size=len(content_bytes),
            mime_type=mime,
            media_type=media_type,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return {
            "success": True,
            "file_id": file_id,
            "filename": save_name,
            "path": str(save_path),
            "size": len(content_bytes),
            "media_id": asset.id,
            "media_type": media_type,
        }
    finally:
        db.close()


@router.get("/media")
def list_media(media_type: str = "", tag: str = ""):
    """List uploaded media assets."""
    db = get_db_sync()
    try:
        query = db.query(MediaAsset)
        if media_type:
            query = query.filter(MediaAsset.media_type == media_type)
        if tag:
            query = query.filter(MediaAsset.tags.contains(tag))
        assets = query.order_by(MediaAsset.created_at.desc()).limit(100).all()
        return {
            "assets": [
                {
                    "id": a.id,
                    "filename": a.filename,
                    "file_path": a.file_path,
                    "file_size": a.file_size,
                    "mime_type": a.mime_type,
                    "media_type": a.media_type,
                    "tags": a.tags or [],
                    "usage_count": a.usage_count,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in assets
            ],
            "total": len(assets),
        }
    finally:
        db.close()


@router.delete("/media/{media_id}")
def delete_media(media_id: int):
    """Delete a media asset."""
    db = get_db_sync()
    try:
        asset = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Media not found")
        # Delete file from disk
        try:
            os.remove(asset.file_path)
        except OSError:
            pass
        db.delete(asset)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    finally:
        db.close()


# ── AI Content Generation ─────────────────────────────────────────────
@router.post("/ai/generate")
def ai_generate(data: dict):
    """AI-assisted content generation."""
    from backend.ai import generate_content

    platform = data.get("platform", "weibo")
    topic = data.get("topic", "")
    tone = data.get("tone", "casual")
    category = data.get("category", "product")
    content_type = data.get("content_type", "text")

    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")

    result = generate_content(platform, topic, tone, category, content_type=content_type)
    return {"success": True, **result}


@router.post("/ai/hashtags")
def ai_hashtags(data: dict):
    """Generate platform-specific hashtags."""
    from backend.ai import generate_hashtags

    platform = data.get("platform", "weibo")
    topic = data.get("topic", "")
    count = data.get("count", 8)

    if not topic:
        raise HTTPException(status_code=400, detail="Hashtag topic is required")

    tags = generate_hashtags(platform, topic, count)
    return {"success": True, "tags": tags, "platform": platform}


@router.post("")
def create_content(data: ContentCreate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == data.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    content = Content(
        account_id=data.account_id,
        platform=account.platform,
        content_type=data.content_type,
        title=data.title,
        text=data.text,
        tags=data.tags,
        extra=data.extra,
        status="draft",
    )
    db.add(content)
    db.commit()
    db.refresh(content)

    # If schedule_at is provided, create a schedule
    if data.schedule_at:
        try:
            scheduled_dt = datetime.fromisoformat(data.schedule_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid schedule_at format, use ISO format")

        schedule = Schedule(
            account_id=data.account_id,
            content_id=content.id,
            platform=account.platform,
            scheduled_at=scheduled_dt,
            status="pending",
        )
        db.add(schedule)
        db.commit()

    return {
        "success": True,
        "content": {
            "id": content.id,
            "type": content.content_type,
            "title": content.title,
            "status": content.status,
        },
    }


@router.get("")
def list_content(
    account_id: int | None = None,
    platform: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Content)
    if account_id:
        query = query.filter(Content.account_id == account_id)
    if platform:
        query = query.filter(Content.platform == platform)
    if status:
        query = query.filter(Content.status == status)
    contents = query.order_by(Content.created_at.desc()).limit(100).all()

    return {
        "contents": [
            {
                "id": c.id,
                "account_id": c.account_id,
                "platform": c.platform,
                "content_type": c.content_type,
                "title": c.title,
                "text": c.text[:200] + "..." if len(c.text) > 200 else c.text,
                "tags": c.tags,
                "media_paths": c.media_paths,
                "status": c.status,
                "platform_post_id": c.platform_post_id,
                "error_message": c.error_message,
                "created_at": c.created_at.isoformat(),
                "published_at": c.published_at.isoformat() if c.published_at else None,
            }
            for c in contents
        ],
        "total": len(contents),
    }


@router.get("/{content_id}")
def get_content(content_id: int, db: Session = Depends(get_db)):
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return {
        "id": content.id,
        "account_id": content.account_id,
        "platform": content.platform,
        "content_type": content.content_type,
        "title": content.title,
        "text": content.text,
        "tags": content.tags,
        "media_paths": content.media_paths,
        "extra": content.extra,
        "status": content.status,
        "platform_post_id": content.platform_post_id,
        "error_message": content.error_message,
        "created_at": content.created_at.isoformat(),
        "published_at": content.published_at.isoformat() if content.published_at else None,
    }


@router.put("/{content_id}")
def update_content(content_id: int, data: ContentUpdate, db: Session = Depends(get_db)):
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if data.title is not None:
        content.title = data.title
    if data.text is not None:
        content.text = data.text
    if data.tags is not None:
        content.tags = data.tags
    if data.extra is not None:
        content.extra = data.extra

    db.commit()
    return {"success": True}


@router.post("/{content_id}/publish")
async def publish_content(content_id: int, account_id: int | None = None, db: Session = Depends(get_db)):
    """Publish content immediately. If account_id is given, publish to that account (for multi-account)."""
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    target_account_id = account_id or content.account_id
    account = db.query(Account).filter(Account.id == target_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    credentials = {}
    if account.credentials_encrypted:
        from backend.crypto import decrypt_credentials
        credentials = decrypt_credentials(account.credentials_encrypted)
    elif account.cookies_encrypted if hasattr(account, 'cookies_encrypted') else False:
        credentials = json.loads(account.cookies_encrypted)
    platform = get_platform(account.platform)

    publish_data = {
        "content_type": content.content_type,
        "title": content.title,
        "text": content.text,
        "media_paths": content.media_paths,
        "tags": content.tags,
        "extra": content.extra,
    }

    import time
    start = time.time()
    result = await platform.publish(credentials, publish_data)
    elapsed = int((time.time() - start) * 1000)

    # Create publish log
    log = PublishLog(
        account_id=target_account_id,
        content_id=content.id,
        platform=account.platform,
        action="publish",
        status="success" if result.get("success") else "failed",
        platform_response=result,
        error_message=result.get("error", ""),
        duration_ms=elapsed,
    )
    db.add(log)

    if result.get("success"):
        content.status = "published"
        content.platform_post_id = result.get("post_id", "")
        content.published_at = datetime.now(timezone.utc)
        account.last_active_at = datetime.now(timezone.utc)
    else:
        content.status = "failed"
        content.error_message = result.get("error", "")

    db.commit()
    return result


@router.post("/{content_id}/schedule")
def schedule_content(content_id: int, scheduled_at: str, account_ids: list[int] | None = None, db: Session = Depends(get_db)):
    """Schedule content for future publishing to one or more accounts."""
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    try:
        dt = datetime.fromisoformat(scheduled_at)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    targets = account_ids or [content.account_id]
    created = []
    for aid in targets:
        account = db.query(Account).filter(Account.id == aid).first()
        if not account:
            continue
        schedule = Schedule(
            account_id=aid,
            content_id=content.id,
            platform=account.platform,
            scheduled_at=dt,
            status="pending",
        )
        db.add(schedule)
        created.append(aid)

    content.status = "scheduled"
    db.commit()
    return {"success": True, "scheduled_accounts": created, "scheduled_at": scheduled_at}


@router.get("/schedules/all")
def list_schedules(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Schedule)
    if status:
        query = query.filter(Schedule.status == status)
    schedules = query.order_by(Schedule.scheduled_at.asc()).limit(100).all()

    return {
        "schedules": [
            {
                "id": s.id,
                "account_id": s.account_id,
                "content_id": s.content_id,
                "platform": s.platform,
                "scheduled_at": s.scheduled_at.isoformat(),
                "status": s.status,
                "retry_count": s.retry_count,
                "last_error": s.last_error,
            }
            for s in schedules
        ]
    }


@router.delete("/{content_id}")
def delete_content(content_id: int, db: Session = Depends(get_db)):
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    db.delete(content)
    db.commit()
    return {"success": True}
