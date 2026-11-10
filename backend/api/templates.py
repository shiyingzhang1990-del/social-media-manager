"""ContentTemplate CRUD API."""
from fastapi import APIRouter, HTTPException
from backend.database import get_db_sync, ContentTemplate

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
def list_templates(platform: str = "", category: str = ""):
    db = get_db_sync()
    try:
        query = db.query(ContentTemplate)
        if platform:
            query = query.filter(ContentTemplate.platform == platform)
        if category:
            query = query.filter(ContentTemplate.category == category)
        templates = query.order_by(ContentTemplate.use_count.desc()).all()
        return {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "platform": t.platform,
                    "content_type": t.content_type,
                    "title_template": t.title_template,
                    "body_template": t.body_template,
                    "hashtag_template": t.hashtag_template,
                    "category": t.category,
                    "use_count": t.use_count,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in templates
            ]
        }
    finally:
        db.close()


@router.post("")
def create_template(data: dict):
    db = get_db_sync()
    try:
        t = ContentTemplate(
            name=data.get("name", ""),
            platform=data.get("platform", ""),
            content_type=data.get("content_type", "text"),
            title_template=data.get("title_template", ""),
            body_template=data.get("body_template", ""),
            hashtag_template=data.get("hashtag_template", ""),
            category=data.get("category", ""),
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return {"success": True, "template": {"id": t.id, "name": t.name}}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.put("/{template_id}")
def update_template(template_id: int, data: dict):
    db = get_db_sync()
    try:
        t = db.query(ContentTemplate).filter(ContentTemplate.id == template_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Template not found")
        for key in ["name", "platform", "content_type", "title_template", "body_template", "hashtag_template", "category"]:
            if key in data:
                setattr(t, key, data[key])
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.delete("/{template_id}")
def delete_template(template_id: int):
    db = get_db_sync()
    try:
        t = db.query(ContentTemplate).filter(ContentTemplate.id == template_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Template not found")
        db.delete(t)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
