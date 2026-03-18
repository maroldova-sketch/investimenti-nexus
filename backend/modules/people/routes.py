import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.core.models.base import get_db
from backend.core.models.kernel import Person, Entity, NexusRole
from backend.core.security.auth import get_current_user, CurrentUser
from .service import (get_all_people, get_person, create_person, update_person,
                      assign_membership, assign_role, get_person_memberships,
                      get_person_roles, get_person_employments, create_employment)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__),"../../..","frontend","templates"))
router = APIRouter(prefix="/people", tags=["people"])

@router.get("", response_class=HTMLResponse)
def people_list(request: Request, db: Session = Depends(get_db),
                cu: CurrentUser = Depends(get_current_user)):
    from sqlalchemy import text as _text
    people = get_all_people(db)
    entities = db.query(Entity).filter(Entity.is_active==True).all()
    # Persons missing key data — for dashboard widget
    incomplete = db.execute(_text("""
        SELECT id, last_name, first_name,
               CASE WHEN rod_cislo IS NULL OR rod_cislo='' THEN 1 ELSE 0 END as no_rc,
               CASE WHEN email_work IS NULL OR email_work='' THEN 1 ELSE 0 END as no_email,
               CASE WHEN phone IS NULL OR phone='' THEN 1 ELSE 0 END as no_phone,
               CASE WHEN birth_date IS NULL OR birth_date='' THEN 1 ELSE 0 END as no_bdate
        FROM person WHERE is_active=1
        AND (rod_cislo IS NULL OR rod_cislo=''
          OR email_work IS NULL OR email_work=''
          OR phone IS NULL OR phone=''
          OR birth_date IS NULL OR birth_date='')
        ORDER BY
          (CASE WHEN rod_cislo IS NULL OR rod_cislo='' THEN 2 ELSE 0 END +
           CASE WHEN email_work IS NULL OR email_work='' THEN 1 ELSE 0 END) DESC,
          last_name
        LIMIT 50
    """)).fetchall()
    incomplete_list = [{'id': r[0], 'name': r[1]+' '+r[2],
                        'missing': (['RC'] if r[3] else []) + (['email'] if r[4] else []) + (['tel'] if r[5] else []) + (['datum nar.'] if r[6] else [])}
                       for r in incomplete]
    return templates.TemplateResponse("pages/people/manager.html", {
        "request": request, "current_user": cu, "active_section": "people",
        "people": people, "entities": entities,
        "now_date": __import__('datetime').date.today().isoformat(),
        "page_title": "Lidé",
        "incomplete": incomplete_list,
        "incomplete_count": len(incomplete_list),
    })

@router.post("/new")
def person_create(
    request: Request,
    first_name: str = Form(...), last_name: str = Form(...),
    email_work: str = Form(None), email_personal: str = Form(None),
    phone: str = Form(None), title_before: str = Form(None),
    db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    if not cu.is_admin_or_owner():
        raise HTTPException(403)
    p = create_person(db, {
        "first_name": first_name, "last_name": last_name,
        "email_work": email_work, "email_personal": email_personal,
        "phone": phone, "title_before": title_before,
    }, cu.person_id, cu.email)
    return RedirectResponse(f"/people/{p.id}", status_code=303)

@router.get("/{person_id}", response_class=HTMLResponse)
def person_detail(person_id: str, request: Request, db: Session = Depends(get_db),
                  cu: CurrentUser = Depends(get_current_user)):
    p = get_person(db, person_id)
    if not p:
        raise HTTPException(404)
    return templates.TemplateResponse("pages/people/detail.html", {
        "request": request, "current_user": cu, "active_section": "people",
        "p": p,
        "memberships": get_person_memberships(db, person_id),
        "roles": get_person_roles(db, person_id),
        "employments": get_person_employments(db, person_id),
        "entities": db.query(Entity).filter(Entity.is_active==True).all(),
        "all_roles": [r.value for r in NexusRole],
        "now_date": __import__('datetime').date.today().isoformat(),
        "page_title": p.full_name,
    })

@router.post("/{person_id}/edit")
def person_edit(person_id: str, first_name: str = Form(...), last_name: str = Form(...),
                email_work: str = Form(None), phone: str = Form(None),
                title_before: str = Form(None), notes: str = Form(None),
                db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    if not cu.is_admin_or_owner():
        raise HTTPException(403)
    update_person(db, person_id, {
        "first_name": first_name, "last_name": last_name,
        "email_work": email_work, "phone": phone,
        "title_before": title_before, "notes": notes,
    }, cu.person_id, cu.email)
    return RedirectResponse(f"/people/{person_id}", status_code=303)

@router.post("/{person_id}/membership")
def add_membership(person_id: str, entity_id: str = Form(...), position: str = Form(None),
                   valid_from: str = Form(None), db: Session = Depends(get_db),
                   cu: CurrentUser = Depends(get_current_user)):
    if not cu.is_admin_or_owner():
        raise HTTPException(403)
    assign_membership(db, person_id, entity_id, position, valid_from, cu.person_id, cu.email)
    return RedirectResponse(f"/people/{person_id}#memberships", status_code=303)

@router.post("/{person_id}/role")
def add_role(person_id: str, role: str = Form(...), scope_type: str = Form("all"),
             scope_entity_id: str = Form(None), db: Session = Depends(get_db),
             cu: CurrentUser = Depends(get_current_user)):
    if not cu.is_admin_or_owner():
        raise HTTPException(403)
    assign_role(db, person_id, role, scope_type, scope_entity_id, cu.person_id, cu.email)
    return RedirectResponse(f"/people/{person_id}#roles", status_code=303)

@router.post("/{person_id}/employment")
def add_employment(person_id: str, entity_id: str = Form(...), position: str = Form(None),
                   employment_type: str = Form("HPP"), date_start: str = Form(...),
                   monthly_gross_kc: str = Form(None), db: Session = Depends(get_db),
                   cu: CurrentUser = Depends(get_current_user)):
    if not cu.is_admin_or_owner():
        raise HTTPException(403)
    create_employment(db, {
        "person_id": person_id, "entity_id": entity_id, "position": position,
        "employment_type": employment_type, "date_start": date_start,
        "monthly_gross_kc": float(monthly_gross_kc) if monthly_gross_kc else None,
    }, cu.person_id, cu.email)
    return RedirectResponse(f"/people/{person_id}#employment", status_code=303)
