import os
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from backend.core.security.auth import get_current_user, CurrentUser
from .data import payload

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '../../..', 'frontend', 'templates'))
router = APIRouter(prefix='/castello/vendors', tags=['castello-vendors'])

@router.get('', response_class=HTMLResponse)
def dashboard(
    request: Request,
    tickets: int = Query(18000, ge=1, le=1000000),
    avg_ticket: float = Query(1200, ge=1, le=100000),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = payload(tickets, avg_ticket)
    return templates.TemplateResponse(
        'pages/castello/vendors.html',
        {'request': request, 'current_user': current_user, 'active_section':'castello-vendors', **data}
    )

@router.get('/api', response_class=JSONResponse)
def api(
    tickets: int = Query(18000, ge=1, le=1000000),
    avg_ticket: float = Query(1200, ge=1, le=100000),
    current_user: CurrentUser = Depends(get_current_user),
):
    return payload(tickets, avg_ticket)
