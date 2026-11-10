"""
Authentication API - user login/logout and platform cookie capture.
"""
import json
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database import (
    get_db_sync, User, LoginSession, hash_password, verify_password, generate_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


# ── Auth dependency ──────────────────────────────────────────────────
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="请先登录")
    db = get_db_sync()
    try:
        user = db.query(User).filter(User.token == credentials.credentials).first()
        if user is None:
            raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
        return user
    finally:
        db.close()


# ── User Auth Models ─────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: str = ""
    username: str = ""
    message: str = ""


class UserResponse(BaseModel):
    success: bool
    username: str = ""


# ── User Auth Endpoints ──────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """Login with username and password."""
    db = get_db_sync()
    try:
        user = db.query(User).filter(User.username == request.username).first()
        if user is None or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        token = generate_token()
        user.token = token
        db.commit()

        return LoginResponse(
            success=True,
            token=token,
            username=user.username,
            message="登录成功",
        )
    finally:
        db.close()


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logout current user."""
    db = get_db_sync()
    try:
        db.query(User).filter(User.id == current_user.id).update({"token": None})
        db.commit()
        return {"success": True, "message": "已退出登录"}
    finally:
        db.close()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current logged-in user info."""
    return UserResponse(success=True, username=current_user.username)


# ── QR Code Login ─────────────────────────────────────────────────────

class QRRequest(BaseModel):
    platform: str


@router.post("/qr/request")
async def request_qr_login(request: QRRequest):
    """Request a QR code login session for a platform."""
    from backend.platforms import get_platform
    if request.platform not in settings.PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {request.platform}")

    platform = get_platform(request.platform)
    result = await platform.request_qr_login()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "QR login not supported"))

    token = generate_token()
    db = get_db_sync()
    try:
        session = LoginSession(
            platform=request.platform,
            session_token=token,
            qr_url=result["qr_url"],
            status="pending",
            expires_at=datetime.fromtimestamp(time.time() + 300),
        )
        db.add(session)
        db.commit()
        return {
            "success": True,
            "session_token": token,
            "qr_url": result["qr_url"],
            "note": result.get("note", ""),
            "expires_in": 300,
        }
    finally:
        db.close()


@router.get("/qr/status/{session_token}")
def get_qr_status(session_token: str):
    """Poll QR login status for a session."""
    db = get_db_sync()
    try:
        session = db.query(LoginSession).filter(
            LoginSession.session_token == session_token
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if datetime.now(timezone.utc) > session.expires_at.replace(tzinfo=timezone.utc):
            session.status = "expired"
            db.commit()
        return {
            "success": True,
            "status": session.status,
            "session_token": session_token,
        }
    finally:
        db.close()


@router.post("/qr/cancel/{session_token}")
def cancel_qr_login(session_token: str):
    """Cancel a pending QR login session."""
    db = get_db_sync()
    try:
        session = db.query(LoginSession).filter(
            LoginSession.session_token == session_token
        ).first()
        if session:
            session.status = "expired"
            db.commit()
        return {"success": True, "message": "QR login cancelled"}
    finally:
        db.close()


@router.post("/qr/confirm/{session_token}")
def confirm_qr_login(session_token: str, credentials: dict[str, Any] = None):
    """Confirm QR login and store credentials (for demo/stub mode)."""
    db = get_db_sync()
    try:
        session = db.query(LoginSession).filter(
            LoginSession.session_token == session_token
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session.status = "confirmed"
        if credentials:
            from backend.crypto import encrypt_credentials
            session.credential_data = encrypt_credentials(credentials)
        db.commit()
        return {"success": True, "message": "QR login confirmed"}
    finally:
        db.close()


# ── Platform Credential Methods ───────────────────────────────────────

@router.get("/credential-methods/{platform}")
def get_credential_methods(platform: str):
    """Get available credential/login methods for a platform."""
    from backend.platforms import get_platform
    if platform not in settings.PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    p = get_platform(platform)
    return {
        "platform": platform,
        "methods": p.get_credential_methods(),
    }


@router.get("/credential-fields/{platform}/{method}")
def get_credential_fields(platform: str, method: str):
    """Get credential form fields for a platform and login method."""
    from backend.platforms import get_platform
    if platform not in settings.PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    p = get_platform(platform)
    return {
        "platform": platform,
        "method": method,
        "fields": p.get_credential_fields_for_method(method),
    }


# ── Platform Cookie Capture ──────────────────────────────────────────
_captured_cookies: dict[str, dict] = {}
_capture_lock = threading.Lock()


class CookieCaptureRequest(BaseModel):
    platform: str
    cookies: dict[str, Any]
    nickname: str = ""
    user_id: str = ""


class RawCookieCaptureRequest(BaseModel):
    """Accepts raw cookie data in various formats."""
    platform: str
    cookies_raw: str
    nickname: str = ""
    user_id: str = ""


@router.get("/platforms")
def get_auth_methods():
    return {
        "platforms": [
            {
                "key": "xiaohongshu",
                "name": "小红书",
                "auth_methods": [
                    {
                        "type": "application_tab",
                        "label": "F12 → Application → Cookies 导出（最可靠，捕获所有Cookie）",
                        "description": "适用于 HttpOnly Cookie",
                    },
                    {
                        "type": "bookmarklet",
                        "label": "书签栏一键获取",
                        "description": "简单快捷，但部分Cookie可能获取不到",
                    },
                ],
            },
            {
                "key": "weibo",
                "name": "微博",
                "auth_methods": [
                    {
                        "type": "bookmarklet",
                        "label": "一键获取 Cookie",
                        "description": "登录微博后点击书签栏按钮",
                    },
                ],
            },
            {
                "key": "bilibili",
                "name": "B站",
                "auth_methods": [
                    {
                        "type": "bookmarklet",
                        "label": "一键获取 Cookie",
                        "description": "登录B站后点击书签栏按钮",
                    },
                ],
            },
            {
                "key": "wechat",
                "name": "微信",
                "auth_methods": [
                    {
                        "type": "manual",
                        "label": "填写 AppID / AppSecret",
                        "description": "使用微信开放平台的应用凭证",
                    },
                ],
            },
            {
                "key": "douyin",
                "name": "抖音",
                "auth_methods": [
                    {
                        "type": "manual",
                        "label": "填写 OpenID / Access Token",
                        "description": "使用抖音开放平台的接口凭证",
                    },
                ],
            },
        ]
    }


@router.post("/capture-cookies")
def capture_cookies(request: CookieCaptureRequest):
    """Accept cookies captured from the browser bookmarklet/console script."""
    if request.platform not in settings.PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {request.platform}")

    session_id = f"{request.platform}_{int(time.time())}"

    with _capture_lock:
        creds: dict[str, Any] = {"cookies": json.dumps(request.cookies)}
        if request.platform == "xiaohongshu":
            creds["user_id"] = request.user_id or request.cookies.get("x-user-id", "")
        elif request.platform == "weibo":
            creds["uid"] = request.user_id or request.cookies.get("UID", "")
        elif request.platform == "bilibili":
            creds["csrf"] = request.cookies.get("bili_jct", "")
            creds["mid"] = request.user_id or ""

        cookie_keys = list(request.cookies.keys()) if isinstance(request.cookies, dict) else []
        if request.platform == "xiaohongshu" and "web_session" not in cookie_keys:
            creds["_warning"] = "未检测到 web_session Cookie，可能无法验证通过"

        _captured_cookies[session_id] = {
            "platform": request.platform,
            "credentials": creds,
            "nickname": request.nickname or "",
            "captured_at": time.time(),
        }

    now = time.time()
    stale = [k for k, v in _captured_cookies.items() if now - v["captured_at"] > 300]
    for k in stale:
        _captured_cookies.pop(k, None)

    return {
        "success": True,
        "session_id": session_id,
        "message": f"{settings.PLATFORM_NAMES.get(request.platform, request.platform)} Cookie 已捕获",
    }


@router.post("/capture-raw-cookies")
def capture_raw_cookies(request: RawCookieCaptureRequest):
    """Accept cookies as a raw string (from Application tab export or document.cookie)."""
    if request.platform not in settings.PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {request.platform}")

    raw = request.cookies_raw.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Cookie 内容为空")

    parsed = None
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            pass
    elif raw.startswith("[{") or raw.startswith("["):
        try:
            arr = json.loads(raw)
            if isinstance(arr, list):
                parsed = {item.get("name", ""): item.get("value", "") for item in arr if "name" in item}
        except json.JSONDecodeError:
            pass

    if parsed is None:
        parts = raw.replace(";", "&").split("&")
        parsed = {}
        for part in parts:
            part = part.strip()
            if "=" in part:
                eq = part.index("=")
                k = part[:eq].strip()
                v = part[eq+1:].strip()
                if k:
                    parsed[k] = v

    if not parsed:
        raise HTTPException(status_code=400, detail="无法解析 Cookie 数据")

    session_id = f"{request.platform}_{int(time.time())}"
    creds: dict[str, Any] = {"cookies": json.dumps(parsed)}
    if request.platform == "xiaohongshu":
        creds["user_id"] = request.user_id or parsed.get("x-user-id", "")

    with _capture_lock:
        _captured_cookies[session_id] = {
            "platform": request.platform,
            "credentials": creds,
            "nickname": request.nickname or "",
            "captured_at": time.time(),
        }

    return {
        "success": True,
        "session_id": session_id,
        "cookie_count": len(parsed),
        "has_session": "web_session" in parsed,
        "message": f"已捕获 {len(parsed)} 个 Cookie 项",
    }


@router.get("/captured/{platform}")
def get_captured_cookies(platform: str):
    """Poll for recently captured cookies."""
    now = time.time()
    with _capture_lock:
        matches = [
            {
                "session_id": k,
                "credentials": v["credentials"],
                "nickname": v["nickname"],
                "captured_at": v["captured_at"],
            }
            for k, v in _captured_cookies.items()
            if v["platform"] == platform and now - v["captured_at"] < 300
        ]
        if matches:
            matches.sort(key=lambda x: x["captured_at"], reverse=True)
            return {"success": True, "capture": matches[0]}
        return {"success": False, "capture": None}


@router.get("/bookmarklet-script/{platform}")
def get_bookmarklet_script(platform: str):
    """Return the bookmarklet JavaScript code."""
    scripts = {
        "xiaohongshu": """
(function(){
  var c = Object.fromEntries(document.cookie.split('; ').map(function(p){var i=p.indexOf('='); return [p.slice(0,i), p.slice(i+1)]}));
  var uid = c['x-user-id'] || '';
  var hasSession = !!c['web_session'];
  fetch('http://127.0.0.1:8765/api/auth/capture-cookies', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({platform:'xiaohongshu', cookies: c, user_id: uid})
  }).then(function(r){return r.json()}).then(function(d){
    if(hasSession){alert('Cookie已捕获！请回到管理系统继续添加账号');}
    else{alert('Cookie已捕获，但缺少web_session（HttpOnly Cookie）建议使用 F12→Application→Cookies 导出');}
  }).catch(function(e){alert('捕获失败: ' + e.message);});
})();
""",
        "weibo": """
(function(){
  var c = Object.fromEntries(document.cookie.split('; ').map(function(p){var i=p.indexOf('='); return [p.slice(0,i), p.slice(i+1)]}));
  fetch('http://127.0.0.1:8765/api/auth/capture-cookies', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({platform:'weibo', cookies: c, user_id: c['UID'] || ''})
  }).then(function(r){return r.json()}).then(function(d){
    alert('Cookie已捕获！请回到管理系统继续添加账号');
  }).catch(function(e){alert('捕获失败: ' + e.message);});
})();
""",
        "bilibili": """
(function(){
  var c = Object.fromEntries(document.cookie.split('; ').map(function(p){var i=p.indexOf('='); return [p.slice(0,i), p.slice(i+1)]}));
  fetch('http://127.0.0.1:8765/api/auth/capture-cookies', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({platform:'bilibili', cookies: c, user_id: c['DedeUserID'] || ''})
  }).then(function(r){return r.json()}).then(function(d){
    alert('Cookie已捕获！请回到管理系统继续添加账号');
  }).catch(function(e){alert('捕获失败: ' + e.message);});
})();
""",
    }
    script = scripts.get(platform)
    if not script:
        raise HTTPException(status_code=404, detail=f"No bookmarklet for platform: {platform}")

    minified = "".join(line.strip() for line in script.split("\n"))
    return {"script": minified, "platform": platform}


# ── Init Default Admin ────────────────────────────────────────────────
def create_default_admin():
    """Create a default admin user if none exists."""
    db = get_db_sync()
    try:
        if db.query(User).count() == 0:
            user = User(
                username="admin",
                password_hash=hash_password("admin123"),
            )
            db.add(user)
            db.commit()
    finally:
        db.close()
