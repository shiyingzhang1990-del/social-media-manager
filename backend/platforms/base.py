"""
Base platform interface. All platform integrations inherit from this.
"""
from abc import ABC, abstractmethod
from typing import Any


class BasePlatform(ABC):
    """Abstract base class for all social media platform integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform identifier, e.g. 'weibo'."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name, e.g. '微博'."""
        ...

    @abstractmethod
    async def verify_account(self, credentials: dict[str, Any]) -> dict[str, Any]:
        """Verify account credentials and return account info."""
        ...

    @abstractmethod
    async def publish(self, account_credentials: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
        """Publish content to the platform."""
        ...

    @abstractmethod
    async def upload_media(self, account_credentials: dict[str, Any], file_path: str, media_type: str) -> dict[str, Any]:
        """Upload a media file (image/video) to the platform."""
        ...

    async def delete_post(self, account_credentials: dict[str, Any], post_id: str) -> dict[str, Any]:
        return {"success": False, "error": "Not implemented"}

    async def get_account_info(self, account_credentials: dict[str, Any]) -> dict[str, Any]:
        return {"success": False, "error": "Not implemented"}

    async def get_post_stats(self, account_credentials: dict[str, Any], post_id: str) -> dict[str, Any]:
        return {"success": False, "error": "Not implemented"}

    # ── Credential Methods ──────────────────────────────────────────────

    def get_credential_methods(self) -> list[dict[str, Any]]:
        """Return available login methods for this platform."""
        return [
            {"type": "password", "label": "用户名/密码登录", "supported": False},
            {"type": "qr", "label": "扫码登录", "supported": False},
            {"type": "cookie", "label": "Cookie 登录", "supported": True},
            {"type": "token", "label": "Token/API 凭证", "supported": False},
        ]

    def get_required_credential_fields(self) -> list[dict[str, Any]]:
        """Return fields needed for credential input forms."""
        return [
            {"key": "cookies", "label": "Cookies (JSON)", "type": "textarea", "required": True},
        ]

    def get_credential_fields_for_method(self, method: str) -> list[dict[str, Any]]:
        """Return credential fields specific to a login method."""
        if method == "password":
            return [
                {"key": "username", "label": "用户名/手机号", "type": "text", "required": True},
                {"key": "password", "label": "密码", "type": "password", "required": True},
            ]
        elif method == "token":
            return [
                {"key": "access_token", "label": "Access Token", "type": "password", "required": True},
                {"key": "refresh_token", "label": "Refresh Token", "type": "password", "required": False},
            ]
        return self.get_required_credential_fields()

    # ── New Auth Methods ────────────────────────────────────────────────

    async def login_with_password(self, username: str, password: str) -> dict[str, Any]:
        """Login using username/password. Returns credentials dict on success."""
        return {"success": False, "error": f"{self.display_name} 暂不支持用户名密码登录，请使用其他方式"}

    async def request_qr_login(self) -> dict[str, Any]:
        """Request a QR code login session. Returns {qr_url, session_token}."""
        return {"success": False, "error": f"{self.display_name} 暂不支持扫码登录"}

    async def check_qr_status(self, session_token: str) -> dict[str, Any]:
        """Poll QR login status. Returns {status, credentials?}."""
        return {"success": False, "status": "expired", "error": "Not supported"}

    async def get_health_status(self, credentials: dict[str, Any]) -> dict[str, Any]:
        """Check account health: login status, rate limits, bans."""
        return {"healthy": True, "issues": []}

    def get_optimal_publish_times(self) -> list[dict[str, Any]]:
        """Return platform-specific optimal publishing time windows."""
        return []

    def get_content_limits(self) -> dict[str, Any]:
        """Return platform content limits."""
        return {
            "max_text_length": 2000,
            "max_images": 9,
            "max_hashtags": 10,
            "supported_types": ["text", "image", "video"],
        }

    # ── Helpers ─────────────────────────────────────────────────────────
    def _parse_cookies(self, raw: Any) -> dict[str, str]:
        """Parse cookies from various formats into a dict."""
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            import json
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                result = {}
                for part in raw.replace(";", "&").split("&"):
                    part = part.strip()
                    if "=" in part:
                        idx = part.index("=")
                        k = part[:idx].strip()
                        v = part[idx+1:].strip()
                        if k:
                            result[k] = v
                return result
        return {}
