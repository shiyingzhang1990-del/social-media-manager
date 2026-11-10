"""
WeChat (微信) platform integration.
Supports WeChat Official Accounts (公众号) publishing via API.
"""
import json
from typing import Any
import httpx
from backend.platforms.base import BasePlatform


class WechatPlatform(BasePlatform):
    @property
    def name(self) -> str:
        return "wechat"

    @property
    def display_name(self) -> str:
        return "微信"

    def get_required_credential_fields(self) -> list[dict[str, Any]]:
        return [
            {"key": "app_id", "label": "AppID / 微信号", "type": "text", "required": True},
            {"key": "app_secret", "label": "AppSecret", "type": "password", "required": True},
            {"key": "token", "label": "Token (可选)", "type": "text", "required": False},
        ]

    def get_credential_methods(self) -> list[dict[str, Any]]:
        return [
            {"type": "token", "label": "公众号 API 凭证", "supported": True},
            {"type": "qr", "label": "公众号扫码授权", "supported": True},
        ]

    def get_credential_fields_for_method(self, method: str) -> list[dict[str, Any]]:
        if method == "token":
            return self.get_required_credential_fields()
        return super().get_credential_fields_for_method(method)

    async def login_with_password(self, username: str, password: str) -> dict[str, Any]:
        return {"success": False, "error": "微信公众号使用AppID/AppSecret验证。请在微信公众平台 (mp.weixin.qq.com) 获取。"}

    async def request_qr_login(self) -> dict[str, Any]:
        import io, base64
        try:
            import qrcode as qrcode_lib
        except ImportError:
            return {"success": False, "error": "QR code library not installed"}
        buf = io.BytesIO()
        img = qrcode_lib.make("https://mp.weixin.qq.com/")
        img.save(buf, format="PNG")
        return {"success": True,
                "qr_url": f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}",
                "note": "请扫描二维码访问微信公众平台。使用AppID/AppSecret完成配置。"}

    async def get_health_status(self, credentials: dict[str, Any]) -> dict[str, Any]:
        result = await self.verify_account(credentials)
        if result.get("success"):
            return {"healthy": True, "issues": []}
        return {"healthy": False, "issues": [result.get("error", "验证失败")]}

    def get_optimal_publish_times(self) -> list[dict[str, Any]]:
        return [
            {"day": "weekday", "start": 7, "end": 9, "score": 0.9},
            {"day": "weekday", "start": 12, "end": 13, "score": 0.8},
            {"day": "weekday", "start": 18, "end": 20, "score": 0.85},
        ]

    def get_content_limits(self) -> dict[str, Any]:
        return {"max_text_length": 20000, "max_images": 8, "max_hashtags": 0,
                "supported_types": ["text", "image", "article"]}

    async def _get_access_token(self, app_id: str, app_secret: str) -> str | None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.weixin.qq.com/cgi-bin/token",
                params={"grant_type": "client_credential", "appid": app_id, "secret": app_secret},
            )
            data = resp.json()
            return data.get("access_token")

    async def verify_account(self, credentials: dict[str, Any]) -> dict[str, Any]:
        app_id = credentials.get("app_id", "")
        app_secret = credentials.get("app_secret", "")
        if not app_id or not app_secret:
            username = credentials.get("username", "")
            if username:
                return {"success": True, "nickname": username, "note": "账号已保存。微信需通过开放平台获取AppID和AppSecret"}
            return {"success": False, "error": "请提供有效的凭证"}
        try:
            token = await self._get_access_token(app_id, app_secret)
            if token:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        "https://api.weixin.qq.com/cgi-bin/account/getaccountbasicinfo",
                        params={"access_token": token},
                    )
                    data = resp.json()
                    return {
                        "success": True,
                        "nickname": data.get("nick_name", "WeChat Account"),
                        "app_id": app_id,
                    }
            return {"success": False, "error": "Failed to get access token"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def upload_media(self, account_credentials: dict[str, Any], file_path: str, media_type: str) -> dict[str, Any]:
        try:
            token = await self._get_access_token(
                account_credentials.get("app_id", ""), account_credentials.get("app_secret", "")
            )
            if not token:
                return {"success": False, "error": "No access token"}
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(file_path, "rb") as f:
                    files = {"media": ("file", f, "image/png" if "image" in media_type else "video/mp4")}
                    resp = await client.post(
                        "https://api.weixin.qq.com/cgi-bin/material/add_material",
                        params={"access_token": token, "type": media_type},
                        files=files,
                    )
                data = resp.json()
                if "media_id" in data:
                    return {"success": True, "media_id": data["media_id"]}
                return {"success": False, "error": str(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def publish(self, account_credentials: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
        try:
            token = await self._get_access_token(
                account_credentials.get("app_id", ""), account_credentials.get("app_secret", "")
            )
            if not token:
                return {"success": False, "error": "No access token"}

            content_type = content.get("content_type", "text")
            async with httpx.AsyncClient(timeout=30.0) as client:
                if content_type == "article":
                    article_body = {
                        "articles": [{
                            "title": content.get("title", ""),
                            "content": content.get("text", ""),
                            "thumb_media_id": content.get("extra", {}).get("thumb_media_id", ""),
                            "need_open_comment": 1,
                            "only_fans_can_comment": 0,
                        }]
                    }
                    resp = await client.post(
                        "https://api.weixin.qq.com/cgi-bin/draft/add",
                        params={"access_token": token},
                        json=article_body,
                    )
                    data = resp.json()
                    if "media_id" in data:
                        return {"success": True, "post_id": data["media_id"]}
                    return {"success": False, "error": str(data)}
                else:
                    # text/image message - publish as mass send
                    media_ids = []
                    for mp in content.get("media_paths", []):
                        r = await self.upload_media(account_credentials, mp, "image")
                        if r.get("success"):
                            media_ids.append(r["media_id"])

                    body: dict[str, Any] = {}
                    if content_type == "text":
                        body = {"content": content.get("text", "")}
                    elif media_ids:
                        body = {"media_ids": media_ids, "content": content.get("text", "")}

                    resp = await client.post(
                        "https://api.weixin.qq.com/cgi-bin/message/mass/sendall",
                        params={"access_token": token},
                        json=body,
                    )
                    data = resp.json()
                    if data.get("errcode") == 0:
                        return {"success": True, "post_id": str(data.get("msg_id", ""))}
                    return {"success": False, "error": str(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_account_info(self, account_credentials: dict[str, Any]) -> dict[str, Any]:
        try:
            token = await self._get_access_token(
                account_credentials.get("app_id", ""), account_credentials.get("app_secret", "")
            )
            if not token:
                return {"success": False, "error": "No access token"}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.weixin.qq.com/cgi-bin/account/getaccountbasicinfo",
                    params={"access_token": token},
                )
                data = resp.json()
                return {"success": True, "info": data}
        except Exception as e:
            return {"success": False, "error": str(e)}
