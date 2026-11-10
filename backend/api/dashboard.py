"""
Dashboard API routes - provide overview stats and metrics.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db, get_db_sync, Account, Content, Schedule, PublishLog

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_accounts = db.query(Account).count()
    active_accounts = db.query(Account).filter(Account.status == "active").count()
    error_accounts = db.query(Account).filter(Account.status == "error").count()

    total_content = db.query(Content).count()
    draft_content = db.query(Content).filter(Content.status == "draft").count()
    scheduled_content = db.query(Content).filter(Content.status == "scheduled").count()
    published_content = db.query(Content).filter(Content.status == "published").count()
    failed_content = db.query(Content).filter(Content.status == "failed").count()

    pending_schedules = db.query(Schedule).filter(Schedule.status == "pending").count()

    today_published = db.query(PublishLog).filter(
        PublishLog.status == "success",
        PublishLog.created_at >= today_start,
    ).count()

    today_failed = db.query(PublishLog).filter(
        PublishLog.status == "failed",
        PublishLog.created_at >= today_start,
    ).count()

    # Platform breakdown
    platform_counts = db.query(
        Account.platform, func.count(Account.id)
    ).group_by(Account.platform).all()

    return {
        "total_accounts": total_accounts,
        "active_accounts": active_accounts,
        "error_accounts": error_accounts,
        "total_content": total_content,
        "draft_content": draft_content,
        "scheduled_content": scheduled_content,
        "published_content": published_content,
        "failed_content": failed_content,
        "pending_schedules": pending_schedules,
        "today_published": today_published,
        "today_failed": today_failed,
        "platform_accounts": {p: c for p, c in platform_counts},
        "last_updated": now.isoformat(),
    }


@router.get("/recent-activity")
def get_recent_activity(limit: int = 20, db: Session = Depends(get_db)):
    logs = db.query(PublishLog).order_by(PublishLog.created_at.desc()).limit(limit).all()
    return {
        "activities": [
            {
                "id": l.id,
                "account_id": l.account_id,
                "content_id": l.content_id,
                "platform": l.platform,
                "action": l.action,
                "status": l.status,
                "error_message": l.error_message,
                "duration_ms": l.duration_ms,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ]
    }


@router.get("/platform-summary")
def get_platform_summary(db: Session = Depends(get_db)):
    """Returns per-platform account and publish stats."""
    result = {}
    platforms = ["weibo", "wechat", "douyin", "xiaohongshu", "bilibili"]
    platform_names = {
        "weibo": "微博", "wechat": "微信", "douyin": "抖音",
        "xiaohongshu": "小红书", "bilibili": "B站",
    }

    for p in platforms:
        accounts = db.query(Account).filter(Account.platform == p).count()
        active = db.query(Account).filter(Account.platform == p, Account.status == "active").count()
        published = db.query(Content).filter(Content.platform == p, Content.status == "published").count()
        today_pub = db.query(PublishLog).filter(
            PublishLog.platform == p,
            PublishLog.status == "success",
            PublishLog.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
        ).count()

        result[p] = {
            "name": platform_names.get(p, p),
            "total_accounts": accounts,
            "active_accounts": active,
            "total_published": published,
            "today_published": today_pub,
        }

    return {"platforms": result}


@router.get("/calendar")
def get_calendar(year: int = 0, month: int = 0):
    """Get scheduled posts for a specific month (for calendar widget)."""
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month

    month_start = datetime(y, m, 1, tzinfo=timezone.utc)
    if m == 12:
        month_end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        month_end = datetime(y, m + 1, 1, tzinfo=timezone.utc)

    db = get_db_sync()
    try:
        schedules = db.query(Schedule).filter(
            Schedule.scheduled_at >= month_start,
            Schedule.scheduled_at < month_end,
        ).order_by(Schedule.scheduled_at.asc()).all()

        return {
            "year": y,
            "month": m,
            "schedules": [
                {
                    "id": s.id,
                    "account_id": s.account_id,
                    "content_id": s.content_id,
                    "platform": s.platform,
                    "scheduled_at": s.scheduled_at.isoformat(),
                    "status": s.status,
                }
                for s in schedules
            ],
        }
    finally:
        db.close()


@router.get("/next-schedules")
def get_next_schedules(limit: int = 10, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    schedules = db.query(Schedule).filter(
        Schedule.status == "pending",
        Schedule.scheduled_at >= now,
    ).order_by(Schedule.scheduled_at.asc()).limit(limit).all()

    return {
        "schedules": [
            {
                "id": s.id,
                "account_id": s.account_id,
                "content_id": s.content_id,
                "platform": s.platform,
                "scheduled_at": s.scheduled_at.isoformat(),
            }
            for s in schedules
        ]
    }
