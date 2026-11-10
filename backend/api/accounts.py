"""
Account management API - enhanced with batch ops, groups, tags, health, import/export.
"""
import json
import csv
import io
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db, get_db_sync, Account
from backend.crypto import encrypt_credentials, decrypt_credentials
from backend.platforms import get_platform, PLATFORM_REGISTRY
from backend.config import settings

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    platform: str
    credentials: dict[str, Any]
    nickname: str = ""
    credential_type: str = "password"
    group_id: int | None = None
    tags: list[str] = []


class AccountUpdate(BaseModel):
    nickname: str | None = None
    credentials: dict[str, Any] | None = None
    group_id: int | None = None
    tags: list[str] | None = None


# ── Platforms ──────────────────────────────────────────────────────────
@router.get("/platforms")
def list_platforms():
    return {
        "platforms": [
            {
                "key": key,
                "name": PLATFORM_REGISTRY[key]().display_name,
                "credential_fields": PLATFORM_REGISTRY[key]().get_required_credential_fields(),
                "credential_methods": PLATFORM_REGISTRY[key]().get_credential_methods(),
                "capabilities": settings.PLATFORM_CAPABILITIES.get(key, []),
            }
            for key in PLATFORM_REGISTRY
        ]
    }


# ── List / Search ─────────────────────────────────────────────────────
@router.get("")
def list_accounts(
    platform: str = "",
    group_id: int | None = None,
    tag: str = "",
    health_status: str = "",
    credential_type: str = "",
    search: str = "",
):
    db = get_db_sync()
    try:
        query = db.query(Account)
        if platform:
            query = query.filter(Account.platform == platform)
        if group_id is not None:
            query = query.filter(Account.group_id == group_id)
        if tag:
            query = query.filter(Account.tags.contains(tag))
        if health_status:
            query = query.filter(Account.health_status == health_status)
        if credential_type:
            query = query.filter(Account.credential_type == credential_type)
        if search:
            q = f"%{search}%"
            query = query.filter(
                (Account.nickname.ilike(q)) | (Account.username.ilike(q))
            )
        accounts = query.order_by(Account.created_at.desc()).all()
        return {
            "accounts": [_account_to_dict(a) for a in accounts],
            "total": len(accounts),
        }
    finally:
        db.close()


# ── Create ────────────────────────────────────────────────────────────
@router.post("")
async def create_account(data: AccountCreate):
    if data.platform not in PLATFORM_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {data.platform}")

    db = get_db_sync()
    try:
        existing = db.query(Account).filter(Account.platform == data.platform).count()
        if existing >= settings.MAX_ACCOUNTS_PER_PLATFORM:
            raise HTTPException(status_code=400,
                detail=f"该平台已达最大账号数限制({settings.MAX_ACCOUNTS_PER_PLATFORM})")
        total = db.query(Account).count()
        if total >= settings.TOTAL_ACCOUNTS_LIMIT:
            raise HTTPException(status_code=400,
                detail=f"已达总账号数限制({settings.TOTAL_ACCOUNTS_LIMIT})")

        platform = get_platform(data.platform)
        verify_result = await platform.verify_account(data.credentials)

        if not verify_result.get("success"):
            raise HTTPException(status_code=400, detail=verify_result.get("error", "Verification failed"))

        encrypted = encrypt_credentials(data.credentials)
        nickname = data.nickname or verify_result.get("nickname", "")
        username = data.credentials.get("username", verify_result.get("uid", verify_result.get("open_id", "")))

        account = Account(
            platform=data.platform,
            nickname=nickname,
            username=username,
            credential_type=data.credential_type,
            credentials_encrypted=encrypted,
            group_id=data.group_id,
            tags=data.tags or [],
            status="active",
            health_status="healthy",
            health_check_at=datetime.now(timezone.utc),
            meta_info=verify_result,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return {"success": True, "account": {"id": account.id, "platform": account.platform,
                "nickname": account.nickname, "status": account.status,
                "credential_type": account.credential_type}}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ── Read ──────────────────────────────────────────────────────────────
@router.get("/{account_id}")
def get_account(account_id: int):
    db = get_db_sync()
    try:
        a = db.query(Account).filter(Account.id == account_id).first()
        if not a:
            raise HTTPException(status_code=404, detail="Account not found")
        d = _account_to_dict(a)
        if a.credentials_encrypted:
            try:
                d["credentials"] = decrypt_credentials(a.credentials_encrypted)
            except Exception:
                d["credentials"] = {}
        return d
    finally:
        db.close()


# ── Update ────────────────────────────────────────────────────────────
@router.put("/{account_id}")
async def update_account(account_id: int, data: AccountUpdate):
    db = get_db_sync()
    try:
        a = db.query(Account).filter(Account.id == account_id).first()
        if not a:
            raise HTTPException(status_code=404, detail="Account not found")
        if data.nickname is not None:
            a.nickname = data.nickname
        if data.group_id is not None:
            a.group_id = data.group_id
        if data.tags is not None:
            a.tags = data.tags
        if data.credentials is not None:
            platform = get_platform(a.platform)
            verify_result = await platform.verify_account(data.credentials)
            if not verify_result.get("success"):
                raise HTTPException(status_code=400, detail=verify_result.get("error", "Re-verification failed"))
            a.credentials_encrypted = encrypt_credentials(data.credentials)
            a.meta_info = verify_result
            a.health_status = "healthy"
        a.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ── Delete ────────────────────────────────────────────────────────────
@router.delete("/{account_id}")
def delete_account(account_id: int):
    db = get_db_sync()
    try:
        a = db.query(Account).filter(Account.id == account_id).first()
        if not a:
            raise HTTPException(status_code=404, detail="Account not found")
        db.delete(a)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ── Verify / Health ───────────────────────────────────────────────────
@router.post("/{account_id}/verify")
async def verify_account(account_id: int):
    return await _verify(account_id)


@router.post("/{account_id}/health-check")
async def health_check(account_id: int):
    db = get_db_sync()
    try:
        a = db.query(Account).filter(Account.id == account_id).first()
        if not a:
            raise HTTPException(status_code=404, detail="Account not found")
        creds = _get_creds(a)
        platform = get_platform(a.platform)
        result = await platform.get_health_status(creds)
        a.health_status = "healthy" if result.get("healthy") else "error"
        a.health_check_at = datetime.now(timezone.utc)
        a.health_details = {"issues": result.get("issues", [])}
        db.commit()
        return {"success": True, "health_status": a.health_status, "health_details": a.health_details}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# ── Batch Operations ──────────────────────────────────────────────────
@router.post("/batch/verify")
async def batch_verify(data: dict):
    """Verify multiple accounts. Body: {account_ids: [1,2,3]}"""
    ids = data.get("account_ids", [])
    results = []
    for aid in ids:
        r = await _verify(aid)
        results.append({"account_id": aid, "success": r.get("success", False)})
    return {"results": results, "total": len(ids), "success_count": sum(1 for r in results if r["success"])}


@router.post("/batch/health-check")
async def batch_health_check(data: dict):
    """Health-check multiple accounts. Body: {account_ids: [1,2,3]}"""
    ids = data.get("account_ids", [])
    db = get_db_sync()
    results = []
    try:
        for aid in ids:
            a = db.query(Account).filter(Account.id == aid).first()
            if not a:
                results.append({"account_id": aid, "success": False, "error": "Not found"})
                continue
            creds = _get_creds(a)
            platform = get_platform(a.platform)
            r = await platform.get_health_status(creds)
            a.health_status = "healthy" if r.get("healthy") else "error"
            a.health_check_at = datetime.now(timezone.utc)
            a.health_details = {"issues": r.get("issues", [])}
            results.append({"account_id": aid, "success": True, "health_status": a.health_status})
        db.commit()
        return {"results": results, "total": len(ids), "healthy": sum(1 for r in results if r.get("health_status") == "healthy")}
    finally:
        db.close()


@router.post("/batch/move")
def batch_move(data: dict):
    """Move accounts to a group. Body: {account_ids: [1,2], group_id: 3}"""
    db = get_db_sync()
    try:
        db.query(Account).filter(Account.id.in_(data.get("account_ids", []))).update(
            {"group_id": data.get("group_id")}, synchronize_session=False
        )
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/batch/tag")
def batch_tag(data: dict):
    """Add or remove tags. Body: {account_ids: [1,2], tags: ["tag1"], action: "add"|"remove"}"""
    db = get_db_sync()
    try:
        accounts = db.query(Account).filter(Account.id.in_(data.get("account_ids", []))).all()
        action = data.get("action", "add")
        tags = data.get("tags", [])
        for a in accounts:
            current = list(a.tags or [])
            if action == "add":
                a.tags = list(set(current + tags))
            elif action == "remove":
                a.tags = [t for t in current if t not in tags]
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.delete("/batch/delete")
def batch_delete(data: dict):
    """Delete multiple accounts. Body: {account_ids: [1,2,3]}"""
    db = get_db_sync()
    try:
        db.query(Account).filter(Account.id.in_(data.get("account_ids", []))).delete(synchronize_session=False)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ── Import / Export ───────────────────────────────────────────────────
@router.post("/batch/import")
async def batch_import(file: UploadFile = File(...), group_id: int | None = None):
    """Import accounts from JSON file."""
    content = await file.read()
    try:
        data = json.loads(content)
        items = data if isinstance(data, list) else data.get("accounts", [])
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    db = get_db_sync()
    success = 0
    errors = []
    try:
        for item in items:
            if db.query(Account).count() >= settings.TOTAL_ACCOUNTS_LIMIT:
                errors.append(f"已达到总数限制 {settings.TOTAL_ACCOUNTS_LIMIT}")
                break
            try:
                encrypted = encrypt_credentials(item.get("credentials", {}))
                account = Account(
                    platform=item["platform"],
                    nickname=item.get("nickname", ""),
                    username=item.get("username", ""),
                    credential_type=item.get("credential_type", "password"),
                    credentials_encrypted=encrypted,
                    group_id=item.get("group_id", group_id),
                    tags=item.get("tags", []),
                    platform_user_id=item.get("platform_user_id", ""),
                )
                db.add(account)
                success += 1
            except Exception as e:
                errors.append(str(e))
        db.commit()
        return {"success": True, "imported": success, "errors": errors}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/batch/export")
def batch_export(platform: str = "", group_id: int | None = None):
    """Export accounts as JSON."""
    db = get_db_sync()
    try:
        query = db.query(Account)
        if platform:
            query = query.filter(Account.platform == platform)
        if group_id is not None:
            query = query.filter(Account.group_id == group_id)
        accounts = query.all()
        items = []
        for a in accounts:
            item = _account_to_dict(a)
            if a.credentials_encrypted:
                try:
                    item["credentials"] = decrypt_credentials(a.credentials_encrypted)
                except Exception:
                    item["credentials"] = {}
            else:
                item["credentials"] = {}
            items.append(item)
        return {"accounts": items, "total": len(items), "exported_at": datetime.now(timezone.utc).isoformat()}
    finally:
        db.close()


# ── Helper Functions ──────────────────────────────────────────────────
def _account_to_dict(a: Account) -> dict:
    return {
        "id": a.id,
        "group_id": a.group_id,
        "platform": a.platform,
        "nickname": a.nickname,
        "username": a.username,
        "status": a.status,
        "credential_type": a.credential_type,
        "tags": a.tags or [],
        "health_status": a.health_status,
        "health_check_at": a.health_check_at.isoformat() if a.health_check_at else None,
        "health_details": a.health_details,
        "meta_info": a.meta_info,
        "platform_user_id": a.platform_user_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        "last_active_at": a.last_active_at.isoformat() if a.last_active_at else None,
    }


def _get_creds(a: Account) -> dict:
    if a.credentials_encrypted:
        return decrypt_credentials(a.credentials_encrypted)
    if a.cookies_encrypted:
        try:
            return json.loads(a.cookies_encrypted)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


async def _verify(account_id: int) -> dict:
    db = get_db_sync()
    try:
        a = db.query(Account).filter(Account.id == account_id).first()
        if not a:
            return {"success": False, "error": "Account not found"}
        creds = _get_creds(a)
        platform = get_platform(a.platform)
        result = await platform.verify_account(creds)
        if result.get("success"):
            a.status = "active"
            a.health_status = "healthy"
            a.last_active_at = datetime.now(timezone.utc)
        else:
            a.status = "error"
            a.health_status = "error"
        a.meta_info = result
        db.commit()
        return result
    finally:
        db.close()
