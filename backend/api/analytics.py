"""
Analytics API - cross-platform aggregate stats, trends, publishing analytics.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from backend.database import get_db_sync, Account, Content, Schedule, PublishLog, AnalyticsSnapshot

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
def get_overview(days: int = 30):
    """Cross-platform aggregate stats for the dashboard."""
    db = get_db_sync()
    try:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        total_accounts = db.query(Account).count()
        active_accounts = db.query(Account).filter(Account.status == "active").count()
        error_accounts = db.query(Account).filter(Account.status == "error").count()
        healthy = db.query(Account).filter(Account.health_status == "healthy").count()
        warning = db.query(Account).filter(Account.health_status == "warning").count()
        unhealthy = db.query(Account).filter(Account.health_status == "error").count()

        total_content = db.query(Content).count()
        published = db.query(Content).filter(Content.status == "published").count()
        failed = db.query(Content).filter(Content.status == "failed").count()

        total_publish_attempts = db.query(PublishLog).filter(PublishLog.created_at >= since).count()
        success_publishes = db.query(PublishLog).filter(PublishLog.status == "success", PublishLog.created_at >= since).count()
        success_rate = round(success_publishes / total_publish_attempts * 100, 1) if total_publish_attempts > 0 else 0

        # Platform distribution
        platform_accounts = {}
        for p, cnt in db.query(Account.platform, func.count(Account.id)).group_by(Account.platform).all():
            platform_accounts[p] = cnt

        # Daily publish count for last 7 days
        daily = []
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            cnt = db.query(PublishLog).filter(
                PublishLog.created_at >= day_start,
                PublishLog.created_at < day_end,
            ).count()
            daily.append({"date": day_start.strftime("%m-%d"), "count": cnt})

        # Average publish duration
        avg_duration = db.query(func.avg(PublishLog.duration_ms)).filter(
            PublishLog.status == "success"
        ).scalar() or 0

        pending_schedules = db.query(Schedule).filter(Schedule.status == "pending").count()
        failed_schedules = db.query(Schedule).filter(Schedule.status == "failed").count()

        return {
            "accounts": {
                "total": total_accounts,
                "active": active_accounts,
                "error": error_accounts,
                "healthy": healthy,
                "warning": warning,
                "unhealthy": unhealthy,
            },
            "content": {
                "total": total_content,
                "published": published,
                "failed": failed,
                "success_rate": success_rate,
            },
            "publishing": {
                "total_attempts": total_publish_attempts,
                "success_count": success_publishes,
                "success_rate": success_rate,
                "avg_duration_ms": round(avg_duration, 1),
                "pending_schedules": pending_schedules,
                "failed_schedules": failed_schedules,
            },
            "platform_distribution": platform_accounts,
            "daily_publishes": daily,
            "period_days": days,
        }
    finally:
        db.close()


@router.get("/platform/{platform}")
def get_platform_analytics(platform: str):
    """Per-platform analytics."""
    db = get_db_sync()
    try:
        accounts = db.query(Account).filter(Account.platform == platform).all()
        account_count = len(accounts)
        healthy_count = sum(1 for a in accounts if a.health_status == "healthy")
        warning_count = sum(1 for a in accounts if a.health_status == "warning")
        error_count = sum(1 for a in accounts if a.health_status == "error")

        content_total = db.query(Content).filter(Content.platform == platform).count()
        content_published = db.query(Content).filter(Content.platform == platform, Content.status == "published").count()
        content_failed = db.query(Content).filter(Content.platform == platform, Content.status == "failed").count()

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_pub = db.query(PublishLog).filter(
            PublishLog.platform == platform,
            PublishLog.status == "success",
            PublishLog.created_at >= today_start,
        ).count()

        # Credential type distribution
        cred_types = {}
        for ct, cnt in db.query(Account.credential_type, func.count(Account.id)).filter(
            Account.platform == platform
        ).group_by(Account.credential_type).all():
            cred_types[ct] = cnt

        # Last 7 days publish trend
        daily = []
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            cnt = db.query(PublishLog).filter(
                PublishLog.platform == platform,
                PublishLog.created_at >= day_start,
                PublishLog.created_at < day_end,
            ).count()
            daily.append({"date": day_start.strftime("%m-%d"), "count": cnt})

        return {
            "platform": platform,
            "accounts": {"total": account_count, "healthy": healthy_count, "warning": warning_count, "error": error_count},
            "content": {"total": content_total, "published": content_published, "failed": content_failed},
            "today_published": today_pub,
            "credential_types": cred_types,
            "daily_publishes": daily,
        }
    finally:
        db.close()


@router.get("/account/{account_id}")
def get_account_analytics(account_id: int):
    """Per-account analytics with trend data."""
    db = get_db_sync()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        now = datetime.now(timezone.utc)
        since_30d = now - timedelta(days=30)

        total_content = db.query(Content).filter(Content.account_id == account_id).count()
        published = db.query(Content).filter(Content.account_id == account_id, Content.status == "published").count()
        failed = db.query(Content).filter(Content.account_id == account_id, Content.status == "failed").count()

        publish_attempts = db.query(PublishLog).filter(
            PublishLog.account_id == account_id, PublishLog.created_at >= since_30d
        ).count()
        success_count = db.query(PublishLog).filter(
            PublishLog.account_id == account_id, PublishLog.status == "success", PublishLog.created_at >= since_30d
        ).count()
        success_rate = round(success_count / publish_attempts * 100, 1) if publish_attempts > 0 else 0

        avg_duration = db.query(func.avg(PublishLog.duration_ms)).filter(
            PublishLog.account_id == account_id, PublishLog.status == "success"
        ).scalar() or 0

        # Last 14 days daily publish count
        daily = []
        for i in range(13, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            cnt = db.query(PublishLog).filter(
                PublishLog.account_id == account_id,
                PublishLog.created_at >= day_start,
                PublishLog.created_at < day_end,
            ).count()
            daily.append({"date": day_start.strftime("%m-%d"), "count": cnt})

        pending_schedules = db.query(Schedule).filter(Schedule.account_id == account_id, Schedule.status == "pending").count()

        return {
            "account": {
                "id": account.id,
                "platform": account.platform,
                "nickname": account.nickname,
                "status": account.status,
                "health_status": account.health_status,
                "tags": account.tags or [],
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "last_active_at": account.last_active_at.isoformat() if account.last_active_at else None,
            },
            "content": {"total": total_content, "published": published, "failed": failed},
            "publishing": {
                "attempts_30d": publish_attempts,
                "success_count": success_count,
                "success_rate": success_rate,
                "avg_duration_ms": round(avg_duration, 1),
                "pending_schedules": pending_schedules,
            },
            "daily_publishes": daily,
        }
    finally:
        db.close()


@router.get("/trends")
def get_trends(days: int = 14):
    """Get publishing trends across all platforms."""
    db = get_db_sync()
    try:
        now = datetime.now(timezone.utc)
        platforms_all = ["weibo", "wechat", "douyin", "xiaohongshu", "bilibili"]

        # Per-platform daily trend
        platform_trends = {}
        for plat in platforms_all:
            trend = []
            for i in range(days - 1, -1, -1):
                day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                success = db.query(PublishLog).filter(
                    PublishLog.platform == plat, PublishLog.status == "success",
                    PublishLog.created_at >= day_start, PublishLog.created_at < day_end,
                ).count()
                failed = db.query(PublishLog).filter(
                    PublishLog.platform == plat, PublishLog.status == "failed",
                    PublishLog.created_at >= day_start, PublishLog.created_at < day_end,
                ).count()
                trend.append({
                    "date": day_start.strftime("%m-%d"),
                    "success": success,
                    "failed": failed,
                })
            platform_trends[plat] = trend

        # Hourly distribution
        hourly = [0] * 24
        logs = db.query(PublishLog).filter(PublishLog.created_at >= now - timedelta(days=days)).all()
        for log in logs:
            if log.created_at:
                hour = log.created_at.hour
                hourly[hour] += 1

        return {
            "days": days,
            "platform_trends": platform_trends,
            "hourly_distribution": [{"hour": h, "count": c} for h, c in enumerate(hourly)],
        }
    finally:
        db.close()


@router.get("/publishing-stats")
def get_publishing_stats():
    """Publishing success rates and performance stats."""
    db = get_db_sync()
    try:
        # Overall success rate
        total = db.query(PublishLog).count()
        success = db.query(PublishLog).filter(PublishLog.status == "success").count()
        overall_rate = round(success / total * 100, 1) if total > 0 else 0

        # Per-platform success rate
        platform_stats = {}
        for plat in ["weibo", "wechat", "douyin", "xiaohongshu", "bilibili"]:
            plat_total = db.query(PublishLog).filter(PublishLog.platform == plat).count()
            plat_success = db.query(PublishLog).filter(PublishLog.platform == plat, PublishLog.status == "success").count()
            plat_rate = round(plat_success / plat_total * 100, 1) if plat_total > 0 else 0
            avg_time = db.query(func.avg(PublishLog.duration_ms)).filter(
                PublishLog.platform == plat, PublishLog.status == "success"
            ).scalar() or 0
            platform_stats[plat] = {
                "total": plat_total,
                "success": plat_success,
                "success_rate": plat_rate,
                "avg_duration_ms": round(avg_time, 1),
            }

        # Best hour by success count
        now = datetime.now(timezone.utc)
        hourly = {}
        logs = db.query(PublishLog).filter(PublishLog.created_at >= now - timedelta(days=30)).all()
        for log in logs:
            h = log.created_at.hour if log.created_at else 0
            if h not in hourly:
                hourly[h] = {"total": 0, "success": 0}
            hourly[h]["total"] += 1
            if log.status == "success":
                hourly[h]["success"] += 1

        best_hours = sorted(
            [{"hour": h, "total": v["total"], "success": v["success"],
              "rate": round(v["success"] / v["total"] * 100, 1) if v["total"] > 0 else 0}
             for h, v in hourly.items()],
            key=lambda x: x["rate"], reverse=True
        )[:5]

        # Recent 24h
        last24h = db.query(PublishLog).filter(PublishLog.created_at >= now - timedelta(hours=24)).count()
        last24h_success = db.query(PublishLog).filter(
            PublishLog.created_at >= now - timedelta(hours=24), PublishLog.status == "success"
        ).count()

        return {
            "overall_success_rate": overall_rate,
            "total_publishes": total,
            "total_success": success,
            "platform_stats": platform_stats,
            "best_hours": best_hours,
            "last_24h": {"total": last24h, "success": last24h_success},
        }
    finally:
        db.close()
