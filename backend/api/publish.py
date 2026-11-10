"""
Batch publish API - publish to multiple accounts, smart scheduling, queue management.
"""
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from backend.database import get_db_sync, Account, Content, Schedule, PublishLog
from backend.crypto import decrypt_credentials
from backend.platforms import get_platform

router = APIRouter(prefix="/api/publish", tags=["publish"])


@router.post("/batch")
async def batch_publish(data: dict):
    """Publish one content to multiple accounts at once."""
    content_id = data.get("content_id")
    account_ids = data.get("account_ids", [])
    if not content_id or not account_ids:
        raise HTTPException(status_code=400, detail="content_id and account_ids are required")

    db = get_db_sync()
    try:
        content = db.query(Content).filter(Content.id == content_id).first()
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        results = []
        for aid in account_ids:
            account = db.query(Account).filter(Account.id == aid).first()
            if not account:
                results.append({"account_id": aid, "success": False, "error": "Account not found"})
                continue

            creds = _get_credentials(account)
            platform = get_platform(account.platform)

            publish_data = {
                "content_type": content.content_type,
                "title": content.title,
                "text": content.text,
                "media_paths": content.media_paths,
                "tags": content.tags,
                "extra": content.extra or {},
            }

            import time
            start = time.time()
            result = await platform.publish(creds, publish_data)
            elapsed = int((time.time() - start) * 1000)

            log = PublishLog(
                account_id=aid,
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
                account.last_active_at = datetime.now(timezone.utc)

            results.append({
                "account_id": aid,
                "platform": account.platform,
                "nickname": account.nickname,
                "success": result.get("success", False),
                "error": result.get("error", ""),
                "post_id": result.get("post_id", ""),
                "duration_ms": elapsed,
            })

        # Update content status
        success_count = sum(1 for r in results if r["success"])
        if success_count > 0:
            content.status = "published"
            content.published_at = datetime.now(timezone.utc)

        db.commit()
        return {
            "success": True,
            "results": results,
            "total": len(account_ids),
            "success_count": success_count,
            "fail_count": len(account_ids) - success_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/smart-schedule")
def smart_schedule(data: dict):
    """Schedule content at platform-optimized times."""
    content_id = data.get("content_id")
    account_ids = data.get("account_ids", [])
    if not content_id or not account_ids:
        raise HTTPException(status_code=400, detail="content_id and account_ids are required")

    db = get_db_sync()
    try:
        content = db.query(Content).filter(Content.id == content_id).first()
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        created = []
        now = datetime.now(timezone.utc)
        for aid in account_ids:
            account = db.query(Account).filter(Account.id == aid).first()
            if not account:
                continue

            platform = get_platform(account.platform)
            optimal_time = _pick_optimal_time(platform, now)
            schedule = Schedule(
                account_id=aid,
                content_id=content.id,
                platform=account.platform,
                scheduled_at=optimal_time,
                status="pending",
            )
            db.add(schedule)
            created.append({
                "account_id": aid,
                "platform": account.platform,
                "scheduled_at": optimal_time.isoformat(),
            })

        content.status = "scheduled"
        db.commit()
        return {"success": True, "scheduled": created, "total": len(created)}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/queue")
def list_queue(status: str = "", limit: int = 50):
    """List publish queue: schedules and recent publish logs."""
    db = get_db_sync()
    try:
        # Pending/failed schedules
        sched_query = db.query(Schedule)
        if status:
            sched_query = sched_query.filter(Schedule.status == status)
        else:
            sched_query = sched_query.filter(Schedule.status.in_(["pending", "failed", "publishing"]))
        schedules = sched_query.order_by(Schedule.scheduled_at.asc()).limit(limit).all()

        queue_items = []
        for s in schedules:
            account = db.query(Account).filter(Account.id == s.account_id).first()
            queue_items.append({
                "id": s.id,
                "type": "schedule",
                "account_id": s.account_id,
                "content_id": s.content_id,
                "platform": s.platform,
                "nickname": account.nickname if account else "",
                "scheduled_at": s.scheduled_at.isoformat(),
                "status": s.status,
                "retry_count": s.retry_count,
                "max_retries": s.max_retries,
                "last_error": s.last_error,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })

        # Recent publish logs
        logs = db.query(PublishLog).order_by(PublishLog.created_at.desc()).limit(20).all()
        for log in logs:
            queue_items.append({
                "id": log.id,
                "type": "log",
                "account_id": log.account_id,
                "content_id": log.content_id,
                "platform": log.platform,
                "action": log.action,
                "status": log.status,
                "error_message": log.error_message,
                "duration_ms": log.duration_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })

        return {"queue": queue_items, "total": len(queue_items)}
    finally:
        db.close()


@router.post("/queue/{queue_id}/retry")
async def retry_schedule(queue_id: int):
    """Retry a failed schedule immediately."""
    db = get_db_sync()
    try:
        s = db.query(Schedule).filter(Schedule.id == queue_id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Schedule not found")
        if s.status not in ("failed", "pending"):
            raise HTTPException(status_code=400, detail=f"Cannot retry schedule in status: {s.status}")

        account = db.query(Account).filter(Account.id == s.account_id).first()
        content = db.query(Content).filter(Content.id == s.content_id).first()
        if not account or not content:
            raise HTTPException(status_code=404, detail="Account or content not found")

        creds = _get_credentials(account)
        platform = get_platform(account.platform)

        publish_data = {
            "content_type": content.content_type,
            "title": content.title,
            "text": content.text,
            "media_paths": content.media_paths,
            "tags": content.tags,
            "extra": content.extra or {},
        }

        import time
        start = time.time()
        result = await platform.publish(creds, publish_data)
        elapsed = int((time.time() - start) * 1000)

        log = PublishLog(
            account_id=account.id,
            content_id=content.id,
            platform=account.platform,
            action="retry",
            status="success" if result.get("success") else "failed",
            platform_response=result,
            error_message=result.get("error", ""),
            duration_ms=elapsed,
        )
        db.add(log)

        if result.get("success"):
            s.status = "done"
            s.published_at = datetime.now(timezone.utc)
            content.status = "published"
            content.published_at = datetime.now(timezone.utc)
        else:
            s.retry_count += 1
            s.last_error = result.get("error", "")
            if s.retry_count >= s.max_retries:
                s.status = "failed"
            else:
                s.status = "pending"

        db.commit()
        return {"success": result.get("success", False), **result}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.delete("/queue/{queue_id}")
def cancel_schedule(queue_id: int):
    """Cancel a pending schedule."""
    db = get_db_sync()
    try:
        s = db.query(Schedule).filter(Schedule.id == queue_id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Schedule not found")
        if s.status not in ("pending", "failed"):
            raise HTTPException(status_code=400, detail=f"Cannot cancel schedule in status: {s.status}")
        s.status = "cancelled"
        # Update associated content if no other active schedules
        active = db.query(Schedule).filter(
            Schedule.content_id == s.content_id,
            Schedule.status.in_(["pending", "publishing"]),
        ).count()
        if active == 0:
            content = db.query(Content).filter(Content.id == s.content_id).first()
            if content and content.status == "scheduled":
                content.status = "draft"
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ── Helpers ───────────────────────────────────────────────────────────
def _get_credentials(account: Account) -> dict:
    if account.credentials_encrypted:
        return decrypt_credentials(account.credentials_encrypted)
    if account.cookies_encrypted if hasattr(account, 'cookies_encrypted') else False:
        try:
            return json.loads(account.cookies_encrypted)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def _pick_optimal_time(platform, now: datetime) -> datetime:
    """Pick the next optimal publish time for a platform."""
    optimal_windows = platform.get_optimal_publish_times()
    if not optimal_windows:
        # Default: next hour at :00
        return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    # Find the next upcoming window
    weekday = now.weekday()
    current_hour = now.hour
    day_type = "weekend" if weekday >= 5 else "weekday"

    candidates = []
    for window in optimal_windows:
        if window.get("day") != day_type:
            continue
        start = window["start"]
        if start > current_hour:
            candidates.append(start)

    if candidates:
        next_hour = min(candidates)
    else:
        next_hour = optimal_windows[0]["start"]

    target = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target
