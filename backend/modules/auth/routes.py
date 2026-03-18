from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.models.kernel import UserAccount
from backend.core.security.auth import verify_password, create_token
from backend.core.audit.log import audit
import os

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_HTML = """<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXUS — Přihlášení</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/core@1.0.0-beta21/dist/css/tabler.min.css">
<link rel="stylesheet" href="/static/css/nexus.css">
<style>
body{background:#0f1117;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.login-box{background:#fff;border-radius:12px;padding:40px 44px;width:380px;box-shadow:0 8px 32px rgba(0,0,0,.25)}
.login-logo{font-size:20px;font-weight:700;color:#0f1117;margin-bottom:4px}
.login-sub{font-size:12px;color:#9ba3af;margin-bottom:32px}
.form-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#6b7280;margin-bottom:4px;display:block}
.form-control{width:100%;padding:9px 12px;font-size:14px;border:1px solid #e4e6ea;border-radius:7px;box-sizing:border-box;margin-bottom:16px;font-family:inherit}
.form-control:focus{outline:none;border-color:#1c7ed6;box-shadow:0 0 0 3px rgba(28,126,214,.12)}
.btn-login{width:100%;padding:10px;background:#1c7ed6;color:#fff;border:none;border-radius:7px;font-size:14px;font-weight:600;cursor:pointer;margin-top:4px}
.btn-login:hover{background:#1568c8}
.error{background:#fff5f5;border:1px solid #fca5a5;color:#991b1b;padding:10px 14px;border-radius:7px;font-size:13px;margin-bottom:16px}
</style>
</head>
<body>
<div class="login-box">
  <div class="login-logo">NEXUS</div>
  <div class="login-sub">Holding Operations Console</div>
  {error}
  <form method="post" action="/auth/login">
    <label class="form-label">Email</label>
    <input class="form-control" type="email" name="email" placeholder="admin@holding.local" required autofocus>
    <label class="form-label">Heslo</label>
    <input class="form-control" type="password" name="password" required>
    <button class="btn-login" type="submit">Přihlásit se</button>
  </form>
</div>
</body>
</html>"""

@router.get("/login", response_class=HTMLResponse)
def login_page():
    return HTMLResponse(LOGIN_HTML.replace("{error}", ""))

@router.post("/login", response_class=HTMLResponse)
def login_submit(email: str = Form(...), password: str = Form(...),
                 db: Session = Depends(get_db)):
    user = db.query(UserAccount).filter(
        UserAccount.email == email, UserAccount.is_active == True
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        err = '<div class="error">Nesprávný email nebo heslo.</div>'
        return HTMLResponse(LOGIN_HTML.replace("{error}", err), status_code=401)
    token = create_token({"sub": user.id, "email": user.email})
    audit(db, "LOGIN", "user_account", user.id, user.id, user.email)
    resp = RedirectResponse("/fleet", status_code=303)
    resp.set_cookie("nexus_token", token, httponly=True, max_age=60*480, samesite="lax")
    return resp

@router.get("/logout")
def logout():
    resp = RedirectResponse("/auth/login", status_code=303)
    resp.delete_cookie("nexus_token")
    return resp
