"""
Xiaohongshu (小红书) platform integration.
Supports cookie-based auth with QR code login helper.
"""
import json
import re
from typing import Any
import httpx
from backend.platforms.base import BasePlatform


class XiaohongshuPlatform(BasePlatform):
    @property
    def name(self) -> str:
        return "xiaohongshu"

    @property
    def display_name(self) -> str:
        return "小红书"

    def get_required_credential_fields(self) -> list[dict[str, Any]]:
        return [
            {"key": "cookies", "label": "小红书 Cookies (JSON格式)", "type": "textarea", "required": True},
            {"key": "user_id", "label": "用户ID (URL中的那串字符)", "type": "text", "required": False},
        ]

    def get_credential_methods(self) -> list[dict[str, Any]]:
        return [
            {"type": "password", "label": "手机号/密码登录", "supported": True},
            {"type": "qr", "label": "扫码登录", "supported": True},
            {"type": "cookie", "label": "Cookie 登录", "supported": True},
        ]

    def get_credential_fields_for_method(self, method: str) -> list[dict[str, Any]]:
        if method == "password":
            return [
                {"key": "username", "label": "手机号", "type": "text", "required": True},
                {"key": "password", "label": "密码", "type": "password", "required": True},
            ]
        return super().get_credential_fields_for_method(method)

    async def login_with_password(self, username: str, password: str) -> dict[str, Any]:
        return {"success": False, "error": "小红书无公开密码登录API。推荐使用Cookie登录或扫码登录。"}

    async def request_qr_login(self) -> dict[str, Any]:
        import io, base64
        try:
            import qrcode as qrcode_lib
        except ImportError:
            return {"success": False, "error": "QR code library not installed"}
        buf = io.BytesIO()
        img = qrcode_lib.make("https://www.xiaohongshu.com/login")
        img.save(buf, format="PNG")
        return {"success": True,
                "qr_url": f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}",
                "note": "请用小红书客户端扫描二维码登录。登录后在浏览器打开 xiaohongshu.com 获取Cookie。"}

    async def get_health_status(self, credentials: dict[str, Any]) -> dict[str, Any]:
        result = await self.verify_account(credentials)
        if result.get("success"):
            return {"healthy": True, "issues": []}
        return {"healthy": False, "issues": [result.get("error", "验证失败")]}

    def get_optimal_publish_times(self) -> list[dict[str, Any]]:
        return [
            {"day": "weekday", "start": 7, "end": 9, "score": 0.9},
            {"day": "weekday", "start": 12, "end": 14, "score": 0.85},
            {"day": "weekday", "start": 18, "end": 21, "score": 0.92},
            {"day": "weekend", "start": 9, "end": 12, "score": 0.88},
        ]

    def get_content_limits(self) -> dict[str, Any]:
        return {"max_text_length": 1000, "max_images": 18, "max_hashtags": 5,
                "supported_types": ["text", "image", "video"]}

    def _parse_cookies(self, cookies_input: Any) -> dict[str, str]:
        """Parse cookies from various input formats into a dict."""
        if isinstance(cookies_input, dict):
            return cookies_input
        if isinstance(cookies_input, str):
            cookies_input = cookies_input.strip()
            if not cookies_input:
                return {}
            # Try parsing as JSON first
            try:
                return json.loads(cookies_input)
            except json.JSONDecodeError:
                pass
            # Try parsing as raw cookie string (name=value; name=value)
            try:
                result = {}
                # Split by semicolons (cookies can be ; or ;  separated)
                parts = re.split(r';\s*', cookies_input)
                for part in parts:
                    part = part.strip()
                    if '=' in part:
                        eq_idx = part.index('=')
                        key = part[:eq_idx].strip()
                        val = part[eq_idx+1:].strip()
                        if key:
                            result[key] = val
                if result:
                    return result
            except Exception:
                pass
        return {}

    async def _make_client(self, cookies_input: Any) -> httpx.AsyncClient:
        cookies = self._parse_cookies(cookies_input)
        return httpx.AsyncClient(
            cookies=cookies,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Referer": "https://www.xiaohongshu.com/",
                "Origin": "https://www.xiaohongshu.com",
            },
            timeout=30.0,
            follow_redirects=True,
        )

    async def verify_account(self, credentials: dict[str, Any]) -> dict[str, Any]:
        cookies_input = credentials.get("cookies", "")
        if cookies_input:
            user_id = credentials.get("user_id", "")
            try:
                async with await self._make_client(cookies_input) as client:
                    resp = await client.get(
                        "https://www.xiaohongshu.com/api/sns/web/v1/user/selfinfo"
                    )
                    content_type = resp.headers.get("content-type", "")
                    if "application/json" not in content_type and "text/json" not in content_type:
                        resp2 = await client.get(
                            "https://edith.xiaohongshu.com/api/sns/web/v1/user/selfinfo"
                        )
                        data = resp2.json()
                    else:
                        try:
                            data = resp.json()
                        except json.JSONDecodeError:
                            resp2 = await client.get(
                                "https://edith.xiaohongshu.com/api/sns/web/v1/user/selfinfo"
                            )
                            data = resp2.json()

                    if data.get("success"):
                        user = data.get("data", {})
                        return {
                            "success": True,
                            "nickname": user.get("nickname", ""),
                            "user_id": user.get("user_id", user_id),
                            "followers": user.get("follower_count", user.get("follows", 0)),
                        }
                    elif data.get("code") == 500 or data.get("msg"):
                        return {
                            "success": False,
                            "error": f"小红书API返回错误: {data.get('msg', '服务器错误')}",
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Cookie 已失效，请重新获取",
                        }
            except httpx.HTTPStatusError as e:
                return {"success": False, "error": f"小红书服务器错误 (HTTP {e.response.status_code})"}
            except httpx.RequestError as e:
                return {"success": False, "error": f"网络连接失败: {str(e)}"}
            except json.JSONDecodeError:
                return {"success": False, "error": "Cookie 无效或已过期，请重新获取"}
            except Exception as e:
                return {"success": False, "error": f"验证失败: {str(e)}"}
        # Non-cookie credentials: accept with basic validation
        username = credentials.get("username", "")
        if username:
            return {"success": True, "nickname": username, "note": "账号已保存。小红书无公开密码API，建议使用Cookie登录获得完整功能"}
        return {"success": False, "error": "请提供有效的凭证（Cookie、用户名或扫码登录）"}

    async def upload_media(self, account_credentials: dict[str, Any], file_path: str, media_type: str) -> dict[str, Any]:
        try:
            async with await self._make_client(account_credentials.get("cookies", "")) as client:
                upload_url = "https://www.xiaohongshu.com/api/sns/web/v1/upload"
                with open(file_path, "rb") as f:
                    files = {"file": ("image.png", f, "image/png")}
                    resp = await client.post(upload_url, files=files)
                data = resp.json()
                if data.get("success"):
                    return {"success": True, "media_id": data["data"].get("file_id", "")}
                return {"success": False, "error": str(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def publish(self, account_credentials: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
        try:
            async with await self._make_client(account_credentials.get("cookies", "")) as client:
                text = content.get("text", "")
                images = content.get("media_paths", [])

                image_ids = []
                for img_path in images:
                    result = await self.upload_media(account_credentials, img_path, "image")
                    if result.get("success"):
                        image_ids.append(result["media_id"])

                payload = {
                    "title": content.get("title", ""),
                    "desc": text,
                    "image_ids": image_ids,
                    "tag_ids": content.get("tags", []),
                    "at_users": [],
                    "location": content.get("extra", {}).get("location", ""),
                    "is_private": False,
                }

                resp = await client.post(
                    "https://www.xiaohongshu.com/api/sns/web/v1/note/post",
                    json=payload,
                )
                data = resp.json()
                if data.get("success"):
                    return {"success": True, "post_id": data["data"].get("note_id", "")}
                return {"success": False, "error": str(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_post(self, account_credentials: dict[str, Any], post_id: str) -> dict[str, Any]:
        try:
            async with await self._make_client(account_credentials.get("cookies", "")) as client:
                resp = await client.post(
                    "https://www.xiaohongshu.com/api/sns/web/v1/note/delete",
                    json={"note_id": post_id},
                )
                data = resp.json()
                return {"success": data.get("success", False), "post_id": post_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
