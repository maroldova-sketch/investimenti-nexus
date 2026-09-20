import os
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from backend.core.security.auth import get_current_user, CurrentUser
from backend.modules.citoliby_commerce.engine import build_view

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(prefix="/citoliby/commerce", tags=["citoliby-commerce"])

@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    view = build_view()
    return templates.TemplateResponse(
        "pages/citoliby_commerce/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "active_section": "citoliby-commerce",
            **view,
        },
    )

@router.get("/api/summary", response_class=JSONResponse)
def api_summary(
    tickets: int = Query(18000, ge=1),
    ticket_revenue: float = Query(18000000, ge=0),
    orders: int = Query(9000, ge=1),
    current_user: CurrentUser = Depends(get_current_user),
):
    return build_view(
        {
            "tickets": tickets,
            "ticket_revenue": ticket_revenue,
            "orders": orders,
        }
    )
