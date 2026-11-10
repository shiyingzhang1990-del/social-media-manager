"""
Scheduler engine that checks for pending schedules and publishes them.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from backend.database import get_db_sync, Schedule, Account, Content, PublishLog
from backend.crypto import decrypt_credentials
from backend.platforms import get_platform

logger = logging.getLogger("scheduler")


class SchedulerEngine:
    def __init__(self, poll_interval: int = 30):
        self.poll_interval = poll_interval
        self.scheduler = AsyncIOScheduler()
        self._running = False

    def start(self):
        if self._running:
            return
        self.scheduler.add_job(
            self._check_schedules,
            "interval",
            seconds=self.poll_interval,
            id="check_schedules",
            replace_existing=True,
        )
        self.scheduler.start()
        self._running = True
        logger.info(f"Scheduler started (poll every {self.poll_interval}s)")

    def stop(self):
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Scheduler stopped")

    async def _check_schedules(self):
        """Check for due schedules and publish them."""
        try:
            db: Session = get_db_sync()
            now = datetime.now(timezone.utc)

            due = db.query(Schedule).filter(
                Schedule.status == "pending",
                Schedule.scheduled_at <= now,
            ).limit(10).all()

            for schedule in due:
                await self._execute_schedule(db, schedule)

            db.close()
        except Exception as e:
            logger.error(f"Scheduler check error: {e}")

    async def _execute_schedule(self, db: Session, schedule: Schedule):
        """Execute a single scheduled publish."""
        schedule.status = "publishing"
        db.commit()

        account = db.query(Account).filter(Account.id == schedule.account_id).first()
        content = db.query(Content).filter(Content.id == schedule.content_id).first()

        if not account or not content:
            schedule.status = "failed"
            schedule.last_error = "Account or content not found"
            db.commit()
            return

        try:
            credentials = {}
            if account.credentials_encrypted:
                credentials = decrypt_credentials(account.credentials_encrypted)
            elif account.cookies_encrypted if hasattr(account, 'cookies_encrypted') else False:
                try:
                    credentials = json.loads(account.cookies_encrypted)
                except (json.JSONDecodeError, ValueError):
                    credentials = {}
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
                account_id=account.id,
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
                schedule.status = "done"
                schedule.published_at = datetime.now(timezone.utc)
                content.status = "published"
                content.platform_post_id = result.get("post_id", "")
                content.published_at = datetime.now(timezone.utc)
            else:
                schedule.retry_count += 1
                schedule.last_error = result.get("error", "Unknown error")
                if schedule.retry_count >= schedule.max_retries:
                    schedule.status = "failed"
                    content.status = "failed"
                    content.error_message = schedule.last_error
                else:
                    schedule.status = "pending"

            db.commit()

        except Exception as e:
            schedule.retry_count += 1
            schedule.last_error = str(e)
            if schedule.retry_count >= schedule.max_retries:
                schedule.status = "failed"
            else:
                schedule.status = "pending"
            db.commit()
            logger.error(f"Schedule {schedule.id} execution error: {e}")
