import os, io, csv
from datetime import datetime, date
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from backend.core.models.base import get_db
from backend.core.models.kernel import Person, Entity, EntityMembership
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from backend.modules.attendance.models import (
    AttendancePeriod, AttendanceSubmission, LeaveRequest, ApprovalCase,
    PayrollExportBatch, PeriodStatus, LeaveStatus, ApprovalStatus, ApprovalType, PayrollBatchStatus
)
from backend.modules.people.models import Employment

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__),"../../..","frontend","templates"))
router = APIRouter(tags=["attendance"])

def _ctx(d): d.setdefault("now_date", date.today().isoformat()); return d

# ── ATTENDANCE ──────────────────────────────────────────────────────────
@router.get("/attendance", response_class=HTMLResponse)
def attendance_console(request: Request, db: Session = Depends(get_db),
                       cu: CurrentUser = Depends(get_current_user)):
    periods = db.query(AttendancePeriod).options(
        joinedload(AttendancePeriod.submissions)
    ).order_by(AttendancePeriod.year.desc(), AttendancePeriod.month.desc()).all()
    entities = db.query(Entity).filter(Entity.is_active==True).order_by(Entity.code).all()
    return templates.TemplateResponse("pages/attendance/console.html", _ctx({
        "request": request, "current_user": cu,
        "periods": periods, "entities": entities, "active_section": "attendance",
    }))

@router.post("/attendance/new")
def create_period(entity_id: str = Form(...), year: int = Form(...), month: int = Form(...),
                  db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    if not cu.has_role("owner","admin","manager","hr"): raise HTTPException(403)
    p = AttendancePeriod(entity_id=entity_id, year=year, month=month,
                         status="open", created_by_id=cu.person_id)
    db.add(p); db.commit()
    audit(db, "CREATE", "attendance_period", p.id, cu.id, cu.email, entity_id)
    return RedirectResponse(f"/attendance/{p.id}", status_code=303)

@router.get("/attendance/{period_id}", response_class=HTMLResponse)
def period_detail(period_id: str, request: Request, db: Session = Depends(get_db),
                  cu: CurrentUser = Depends(get_current_user)):
    period = db.query(AttendancePeriod).options(
        joinedload(AttendancePeriod.submissions).joinedload(AttendanceSubmission.person)
    ).filter(AttendancePeriod.id == period_id).first()
    if not period: raise HTTPException(404)
    entity = db.query(Entity).filter(Entity.id == period.entity_id).first()
    members = db.query(EntityMembership).filter(EntityMembership.entity_id == period.entity_id).all()
    people = db.query(Person).filter(Person.id.in_({m.person_id for m in members}), Person.is_active==True).all()
    emp_map = {e.person_id: e for e in db.query(Employment).filter(Employment.entity_id==period.entity_id, Employment.is_active==True).all()}
    sub_map = {s.person_id: s for s in period.submissions}
    exports = db.query(PayrollExportBatch).filter(PayrollExportBatch.period_id==period_id).all()
    return templates.TemplateResponse("pages/attendance/period_detail.html", _ctx({
        "request": request, "current_user": cu, "period": period, "entity": entity,
        "people": people, "sub_map": sub_map, "emp_map": emp_map, "exports": exports,
        "active_section": "attendance",
    }))

@router.post("/attendance/{period_id}/submit")
def submit_period(period_id: str, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    p = db.query(AttendancePeriod).filter(AttendancePeriod.id==period_id).first()
    if not p: raise HTTPException(404)
    if p.status != "open": raise HTTPException(400, f"Status is {p.status}, not open")
    p.status = "submitted"
    db.commit()
    ac = ApprovalCase(case_type="attendance", ref_id=period_id,
                      entity_id=p.entity_id, status="pending")
    db.add(ac); db.commit()
    audit(db, "SUBMIT", "attendance_period", p.id, cu.id, cu.email, p.entity_id)
    return RedirectResponse(f"/attendance/{period_id}", status_code=303)

@router.post("/attendance/{period_id}/approve")
def approve_period(period_id: str, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    if not cu.has_role("owner","admin","manager"): raise HTTPException(403)
    p = db.query(AttendancePeriod).filter(AttendancePeriod.id==period_id).first()
    if not p: raise HTTPException(404)
    if p.status != "submitted": raise HTTPException(400, f"Status is {p.status}, not submitted")
    p.status = "approved"; p.approved_by_id = cu.person_id; p.approved_at = datetime.utcnow()
    db.query(ApprovalCase).filter(ApprovalCase.ref_id==period_id).update({
        "status": "approved", "resolved_by_id": cu.person_id, "resolved_at": datetime.utcnow()
    })
    db.commit()
    audit(db, "APPROVE", "attendance_period", p.id, cu.id, cu.email, p.entity_id)
    return RedirectResponse(f"/attendance/{period_id}", status_code=303)

@router.post("/attendance/{period_id}/lock")
def lock_period(period_id: str, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    if not cu.has_role("owner","admin","hr"): raise HTTPException(403)
    p = db.query(AttendancePeriod).filter(AttendancePeriod.id==period_id).first()
    if not p: raise HTTPException(404)
    if p.status != "approved": raise HTTPException(400, f"Status is {p.status}, not approved")
    p.status = "locked"; p.locked_by_id = cu.person_id; p.locked_at = datetime.utcnow()
    db.commit()
    audit(db, "LOCK", "attendance_period", p.id, cu.id, cu.email, p.entity_id)
    return RedirectResponse(f"/attendance/{period_id}", status_code=303)

@router.post("/attendance/{period_id}/save-row")
def save_row(period_id: str, person_id: str = Form(...),
             days_worked: float = Form(None), hours_worked: float = Form(None),
             days_vacation: float = Form(None), days_sick: float = Form(None),
             gross_salary: float = Form(None), note: str = Form(None),
             db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    period = db.query(AttendancePeriod).filter(AttendancePeriod.id==period_id).first()
    if not period or period.status == "locked": raise HTTPException(400)
    sub = db.query(AttendanceSubmission).filter(
        AttendanceSubmission.period_id==period_id, AttendanceSubmission.person_id==person_id
    ).first()
    if not sub:
        sub = AttendanceSubmission(period_id=period_id, person_id=person_id, entity_id=period.entity_id)
        db.add(sub)
    sub.days_worked=days_worked; sub.hours_worked=hours_worked
    sub.days_vacation=days_vacation; sub.days_sick=days_sick
    sub.gross_salary=gross_salary; sub.note=note
    db.commit()
    audit(db, "UPDATE", "attendance_submission", sub.id, cu.id, cu.email)
    return RedirectResponse(f"/attendance/{period_id}", status_code=303)

@router.post("/attendance/{period_id}/export")
def export_payroll(period_id: str, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    if not cu.has_role("owner","admin","hr","finance"): raise HTTPException(403)
    period = db.query(AttendancePeriod).options(
        joinedload(AttendancePeriod.submissions).joinedload(AttendanceSubmission.person)
    ).filter(AttendancePeriod.id==period_id).first()
    if not period or period.status != "locked": raise HTTPException(400, "Period must be LOCKED")
    entity = db.query(Entity).filter(Entity.id==period.entity_id).first()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Příjmení","Jméno","Email","Dny odprac.","Hodiny","Dovolená","Nemoc","Hrubá mzda","Poznámka"])
    for s in period.submissions:
        p = s.person
        w.writerow([p.last_name, p.first_name, p.email_work or "",
                    s.days_worked or "", s.hours_worked or "",
                    s.days_vacation or "", s.days_sick or "",
                    s.gross_salary or "", s.note or ""])
    import pathlib
    _export_dir = pathlib.Path(os.environ.get("EXPORT_DIR", "") or pathlib.Path(__file__).parent.parent.parent.parent / "exports")
    _export_dir.mkdir(parents=True, exist_ok=True)
    fname = f"payroll_{entity.code}_{period.year}_{period.month:02d}.csv"
    fpath = str(_export_dir / fname)
    with open(fpath, "w", encoding="utf-8-sig", newline="") as f: f.write(buf.getvalue())
    batch = PayrollExportBatch(period_id=period_id, entity_id=period.entity_id,
        status="exported", row_count=len(period.submissions),
        file_path=fpath, exported_by_id=cu.person_id, exported_at=datetime.utcnow())
    db.add(batch); db.commit()
    audit(db, "EXPORT", "payroll_export_batch", batch.id, cu.id, cu.email, period.entity_id, f"rows={batch.row_count}")
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"})

# ── LEAVE ───────────────────────────────────────────────────────────────
@router.get("/leave", response_class=HTMLResponse)
def leave_list(request: Request, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    leaves = db.query(LeaveRequest).options(joinedload(LeaveRequest.person)).order_by(LeaveRequest.created_at.desc()).all()
    entities = db.query(Entity).filter(Entity.is_active==True).order_by(Entity.code).all()
    people = db.query(Person).filter(Person.is_active==True).order_by(Person.last_name).all()
    return templates.TemplateResponse("pages/attendance/leave.html", _ctx({
        "request": request, "current_user": cu,
        "leaves": leaves, "entities": entities, "people": people, "active_section": "attendance",
    }))

@router.post("/leave/new")
def create_leave(person_id: str = Form(...), entity_id: str = Form(...),
                 leave_type: str = Form("dovolená"), date_from: str = Form(...),
                 date_to: str = Form(...), days: float = Form(None), reason: str = Form(None),
                 db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    lr = LeaveRequest(person_id=person_id, entity_id=entity_id,
                      leave_type=leave_type, date_from=date_from, date_to=date_to,
                      days=days, reason=reason, status="submitted")
    db.add(lr); db.flush()
    ac = ApprovalCase(case_type="leave", ref_id=lr.id,
                      entity_id=entity_id, status="pending")
    db.add(ac); db.commit()
    audit(db, "CREATE", "leave_request", lr.id, cu.id, cu.email, entity_id)
    return RedirectResponse("/leave", status_code=303)

@router.post("/leave/{leave_id}/approve")
def approve_leave(leave_id: str, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    if not cu.has_role("owner","admin","manager"): raise HTTPException(403)
    lr = db.query(LeaveRequest).filter(LeaveRequest.id==leave_id).first()
    if not lr: raise HTTPException(404)
    lr.status = "approved"; lr.approved_by_id = cu.person_id; lr.approved_at = datetime.utcnow()
    db.query(ApprovalCase).filter(ApprovalCase.ref_id==leave_id).update({
        "status": "approved", "resolved_by_id": cu.person_id, "resolved_at": datetime.utcnow()
    })
    db.commit()
    audit(db, "APPROVE", "leave_request", lr.id, cu.id, cu.email)
    return RedirectResponse("/leave", status_code=303)

@router.post("/leave/{leave_id}/reject")
def reject_leave(leave_id: str, reject_reason: str = Form(None),
                 db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    if not cu.has_role("owner","admin","manager"): raise HTTPException(403)
    lr = db.query(LeaveRequest).filter(LeaveRequest.id==leave_id).first()
    if not lr: raise HTTPException(404)
    lr.status = "rejected"; lr.reject_reason = reject_reason; lr.approved_by_id = cu.person_id
    db.query(ApprovalCase).filter(ApprovalCase.ref_id==leave_id).update({
        "status": "rejected", "resolved_by_id": cu.person_id,
        "resolved_at": datetime.utcnow(), "note": reject_reason
    })
    db.commit()
    audit(db, "REJECT", "leave_request", lr.id, cu.id, cu.email)
    return RedirectResponse("/leave", status_code=303)

# ── APPROVALS ───────────────────────────────────────────────────────────
@router.get("/approvals", response_class=HTMLResponse)
def approval_center(request: Request, db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    cases = db.query(ApprovalCase).order_by(ApprovalCase.status, ApprovalCase.created_at.desc()).all()
    enriched = []
    for c in cases:
        ref = None
        if c.case_type == "attendance":
            ref = db.query(AttendancePeriod).filter(AttendancePeriod.id==c.ref_id).first()
        elif c.case_type == "leave":
            ref = db.query(LeaveRequest).options(joinedload(LeaveRequest.person)).filter(LeaveRequest.id==c.ref_id).first()
        enriched.append({"case": c, "ref": ref,
                         "entity": db.query(Entity).filter(Entity.id==c.entity_id).first() if c.entity_id else None})
    return templates.TemplateResponse("pages/attendance/approvals.html", _ctx({
        "request": request, "current_user": cu,
        "cases": enriched, "active_section": "approvals",
    }))
