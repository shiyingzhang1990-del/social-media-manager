from backend.api.accounts import router as accounts_router
from backend.api.content import router as content_router
from backend.api.dashboard import router as dashboard_router
from backend.api.groups import router as groups_router
from backend.api.templates import router as templates_router
from backend.api.publish import router as publish_router
from backend.api.analytics import router as analytics_router

__all__ = ["accounts_router", "content_router", "dashboard_router", "groups_router", "templates_router", "publish_router", "analytics_router"]
