"""AccountGroup CRUD API."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.database import get_db_sync, AccountGroup, Account

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("")
def list_groups():
    """List all groups with account counts."""
    db = get_db_sync()
    try:
        groups = db.query(AccountGroup).order_by(AccountGroup.sort_order, AccountGroup.name).all()
        result = []
        for g in groups:
            account_count = db.query(Account).filter(Account.group_id == g.id).count()
            result.append({
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "parent_id": g.parent_id,
                "color": g.color,
                "sort_order": g.sort_order,
                "account_count": account_count,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            })
        return {"groups": result}
    finally:
        db.close()


@router.post("")
def create_group(data: dict):
    """Create a new group."""
    db = get_db_sync()
    try:
        group = AccountGroup(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parent_id=data.get("parent_id"),
            color=data.get("color", "#3699ff"),
            sort_order=data.get("sort_order", 0),
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        return {"success": True, "group": {"id": group.id, "name": group.name}}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.put("/{group_id}")
def update_group(group_id: int, data: dict):
    """Update a group."""
    db = get_db_sync()
    try:
        group = db.query(AccountGroup).filter(AccountGroup.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        for key in ["name", "description", "parent_id", "color", "sort_order"]:
            if key in data:
                setattr(group, key, data[key])
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.delete("/{group_id}")
def delete_group(group_id: int):
    """Delete a group and unlink its accounts."""
    db = get_db_sync()
    try:
        group = db.query(AccountGroup).filter(AccountGroup.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        # Unlink accounts
        db.query(Account).filter(Account.group_id == group_id).update({"group_id": None})
        db.delete(group)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
