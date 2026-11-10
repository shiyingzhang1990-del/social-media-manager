"""
Douyin (抖音) platform integration.
Uses Douyin Open API for content management.
"""
import json
from typing import Any
import httpx
from backend.platforms.base import BasePlatform


class DouyinPlatform(BasePlatform):
    @property
    def name(self) -> str:
        return "douyin"

    @property
    def display_name(self) -> str:
        return "抖音"

    def get_required_credential_fields(self) -> list[dict[str, Any]]:
        return [
            {"key": "open_id", "label": "Open ID", "type": "text", "required": True},
            {"key": "access_token", "label": "Access Token", "type": "password", "required": True},
            {"key": "refresh_token", "label": "Refresh Token", "type": "password", "required": False},
        ]

    def get_credential_methods(self) -> list[dict[str, Any]]:
        return [
            {"type": "token", "label": "Open API 凭证", "supported": True},
            {"type": "qr", "label": "扫码登录", "supported": True},
        ]

    def get_credential_fields_for_method(self, method: str) -> list[dict[str, Any]]:
        if method == "token":
            return self.get_required_credential_fields()
        return super().get_credential_fields_for_method(method)

    async def login_with_password(self, username: str, password: str) -> dict[str, Any]:
        return {"success": False, "error": "抖音需要企业认证才能使用API。请在抖音开放平台 (open.douyin.com) 申请接入。"}

    async def request_qr_login(self) -> dict[str, Any]:
        import io, base64
        try:
            import qrcode as qrcode_lib
        except ImportError:
            return {"success": False, "error": "QR code library not installed"}
        buf = io.BytesIO()
        img = qrcode_lib.make("https://creator.douyin.com/")
        img.save(buf, format="PNG")
        return {"success": True,
                "qr_url": f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}",
                "note": "请用抖音扫描二维码访问创作者平台。抖音需企业认证后使用Open API凭证。"}

    async def get_health_status(self, credentials: dict[str, Any]) -> dict[str, Any]:
        result = await self.verify_account(credentials)
        if result.get("success"):
            return {"healthy": True, "issues": []}
        return {"healthy": False, "issues": [result.get("error", "验证失败")]}

    def get_optimal_publish_times(self) -> list[dict[str, Any]]:
        return [
            {"day": "weekday", "start": 7, "end": 9, "score": 0.85},
            {"day": "weekday", "start": 12, "end": 13, "score": 0.88},
            {"day": "weekday", "start": 18, "end": 22, "score": 0.95},
            {"day": "weekend", "start": 10, "end": 14, "score": 0.9},
            {"day": "weekend", "start": 18, "end": 23, "score": 0.92},
        ]

    def get_content_limits(self) -> dict[str, Any]:
        return {"max_text_length": 500, "max_images": 9, "max_hashtags": 5,
                "supported_types": ["video", "image"]}

    async def _client(self, token: str) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            },
            timeout=30.0,
        )

    async def verify_account(self, credentials: dict[str, Any]) -> dict[str, Any]:
        token = credentials.get("access_token", "")
        open_id = credentials.get("open_id", "")
        if not token and not open_id:
            username = credentials.get("username", "")
            if username:
                return {"success": True, "nickname": username, "note": "账号已保存。抖音需通过企业认证获取API权限"}
            return {"success": False, "error": "请提供有效的凭证"}
        try:
            async with await self._client(token) as client:
                resp = await client.get(
                    "https://open.douyin.com/oauth/userinfo/",
                    params={"open_id": open_id},
                )
                data = resp.json()
                if data.get("message") == "success":
                    user = data.get("data", {})
                    return {
                        "success": True,
                        "nickname": user.get("nickname", ""),
                        "open_id": open_id,
                    }
                return {"success": False, "error": str(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def upload_media(self, account_credentials: dict[str, Any], file_path: str, media_type: str) -> dict[str, Any]:
        try:
            token = account_credentials.get("access_token", "")
            async with await self._client(token) as client:
                with open(file_path, "rb") as f:
                    files = {"video" if "video" in media_type else "image": ("file", f)}
                    resp = await client.post(
                        "https://open.douyin.com/api/douyin/v1/video/upload/",
                        params={"open_id": account_credentials.get("open_id", "")},
                        files=files,
                    )
                data = resp.json()
                if data.get("data", {}).get("item_id"):
                    return {
                        "success": True,
                        "media_id": data["data"]["item_id"],
                    }
                return {"success": False, "error": str(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def publish(self, account_credentials: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
        try:
            token = account_credentials.get("access_token", "")
            async with await self._client(token) as client:
                text = content.get("text", "")
                media_paths = content.get("media_paths", [])

                if content.get("content_type") == "video" and media_paths:
                    video_path = media_paths[0]
                    upload_r = await self.upload_media(account_credentials, video_path, "video")
                    if not upload_r.get("success"):
                        return upload_r

                    payload = {
                        "open_id": account_credentials.get("open_id", ""),
                        "access_token": token,
                        "body": json.dumps({
                            "text": text,
                            "item_id": upload_r["media_id"],
                            "timeline": content.get("extra", {}).get("timeline", ""),
                        }),
                    }
                    resp = await client.post(
                        "https://open.douyin.com/api/douyin/v1/video/create/",
                        json=payload,
                    )
                else:
                    # Image post
                    payload = {
                        "open_id": account_credentials.get("open_id", ""),
                        "access_token": token,
                        "body": json.dumps({
                            "text": text,
                            "image_ids": [],
                        }),
                    }
                    resp = await client.post(
                        "https://open.douyin.com/api/douyin/v1/image/create/",
                        json=payload,
                    )

                data = resp.json()
                if data.get("data", {}).get("item_id"):
                    return {"success": True, "post_id": data["data"]["item_id"]}
                return {"success": False, "error": str(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}
