import os, csv
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from backend.core.models.kernel import Person, Entity
from backend.core.audit.log import audit
from .models import (
    AttendancePeriod, AttendanceSubmission, LeaveRequest, ApprovalCase,
    PayrollExportBatch, PeriodStatus, LeaveStatus, ApprovalStatus, ApprovalType
)
from backend.modules.people.models import Employment

def get_periods(db: Session, entity_id: str = None):
    q = db.query(AttendancePeriod).options(joinedload(AttendancePeriod.entity))
    if entity_id:
        q = q.filter(AttendancePeriod.entity_id == entity_id)
    return q.order_by(AttendancePeriod.year.desc(), AttendancePeriod.month.desc()).all()

def get_period(db: Session, period_id: str) -> AttendancePeriod | None:
    return db.query(AttendancePeriod).options(
        joinedload(AttendancePeriod.submissions).joinedload(AttendanceSubmission.person),
        joinedload(AttendancePeriod.submissions).joinedload(AttendanceSubmission.employment),
        joinedload(AttendancePeriod.entity),
    ).filter(AttendancePeriod.id == period_id).first()

def create_period(db: Session, entity_id: str, year: int, month: int,
                  notes: str = None, actor_id: str = None, actor_email: str = None) -> AttendancePeriod:
    months_cs = ["","Leden","Únor","Březen","Duben","Květen","Červen",
                 "Červenec","Srpen","Září","Říjen","Listopad","Prosinec"]
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    label = f"{months_cs[month]} {year} — {entity.code if entity else '?'}"
    p = AttendancePeriod(entity_id=entity_id, year=year, month=month, label=label,
                         notes=notes, created_by_id=actor_id)
    db.add(p)
    audit(db, "CREATE", "attendance_period", None, actor_id, actor_email,
          entity_id=entity_id, detail=label)
    db.commit()
    db.refresh(p)
    return p

def add_submission(db: Session, period_id: str, person_id: str, data: dict,
                   actor_id: str = None, actor_email: str = None) -> AttendanceSubmission:
    emp = db.query(Employment).filter(
        Employment.person_id == person_id,
        Employment.status == "active",
    ).first()
    s = AttendanceSubmission(
        period_id=period_id,
        person_id=person_id,
        employment_id=emp.id if emp else None,
        monthly_gross_kc=emp.monthly_gross_kc if emp else None,
        submitted_at=datetime.utcnow(),
        **{k: v for k, v in data.items() if v is not None},
    )
    db.add(s)
    audit(db, "CREATE", "attendance_submission", period_id, actor_id, actor_email,
          detail=f"person={person_id}")
    db.commit()
    db.refresh(s)
    return s

def approve_period(db: Session, period_id: str, actor_id: str, actor_email: str):
    p = db.query(AttendancePeriod).filter(AttendancePeriod.id == period_id).first()
    if p and p.status in (PeriodStatus.OPEN, PeriodStatus.SUBMITTED):
        p.status = PeriodStatus.APPROVED
        p.approved_by_id = actor_id
        # create/update approval case
        case = db.query(ApprovalCase).filter(
            ApprovalCase.attendance_period_id == period_id,
            ApprovalCase.approval_type == ApprovalType.ATTENDANCE,
        ).first()
        if not case:
            case = ApprovalCase(attendance_period_id=period_id, approval_type=ApprovalType.ATTENDANCE)
            db.add(case)
        case.status = ApprovalStatus.APPROVED
        case.decided_by_id = actor_id
        case.decided_at = datetime.utcnow()
        audit(db, "UPDATE", "attendance_period", period_id, actor_id, actor_email, detail="approved")
        db.commit()

def lock_period(db: Session, period_id: str, actor_id: str, actor_email: str):
    p = db.query(AttendancePeriod).filter(AttendancePeriod.id == period_id).first()
    if p and p.status == PeriodStatus.APPROVED:
        p.status = PeriodStatus.LOCKED
        p.locked_by_id = actor_id
        p.locked_at = datetime.utcnow()
        audit(db, "UPDATE", "attendance_period", period_id, actor_id, actor_email, detail="locked")
        db.commit()

def create_leave_request(db: Session, person_id: str, entity_id: str, data: dict,
                         actor_id: str = None, actor_email: str = None) -> LeaveRequest:
    lr = LeaveRequest(person_id=person_id, entity_id=entity_id,
                      **{k: v for k, v in data.items() if v})
    db.add(lr)
    db.flush()
    # auto-create approval case
    case = ApprovalCase(
        approval_type=ApprovalType.LEAVE,
        leave_request_id=lr.id,
        created_by_id=actor_id,
    )
    db.add(case)
    audit(db, "CREATE", "leave_request", lr.id, actor_id, actor_email,
          entity_id=entity_id, detail=f"{data.get('leave_type')} {data.get('date_from')}–{data.get('date_to')}")
    db.commit()
    db.refresh(lr)
    return lr

def decide_leave(db: Session, leave_id: str, decision: str, note: str = None,
                 actor_id: str = None, actor_email: str = None):
    lr = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not lr:
        return
    lr.status = LeaveStatus.APPROVED if decision == "approve" else LeaveStatus.REJECTED
    lr.decided_by_id = actor_id
    lr.decided_at = datetime.utcnow()
    lr.decision_note = note
    # update approval case
    case = db.query(ApprovalCase).filter(
        ApprovalCase.leave_request_id == leave_id
    ).first()
    if case:
        case.status = ApprovalStatus.APPROVED if decision == "approve" else ApprovalStatus.REJECTED
        case.decided_by_id = actor_id
        case.decided_at = datetime.utcnow()
        case.note = note
    audit(db, "UPDATE", "leave_request", leave_id, actor_id, actor_email, detail=decision)
    db.commit()

def get_pending_approvals(db: Session, assignee_id: str = None):
    q = db.query(ApprovalCase).options(
        joinedload(ApprovalCase.leave_request).joinedload(LeaveRequest.person),
        joinedload(ApprovalCase.attendance_period).joinedload(AttendancePeriod.entity),
    ).filter(ApprovalCase.status == ApprovalStatus.PENDING)
    return q.order_by(ApprovalCase.created_at.desc()).all()

def generate_payroll_export(db: Session, period_id: str, actor_id: str, actor_email: str) -> PayrollExportBatch:
    period = get_period(db, period_id)
    if not period or period.status != PeriodStatus.LOCKED:
        raise ValueError("Period must be locked before export")

    rows = []
    total_gross = 0.0
    for s in period.submissions:
        gross = float(s.gross_salary or 0)
        total_gross += gross
        rows.append({
            "person_id": s.person_id,
            "full_name": s.person.full_name if s.person else "",
            "entity": period.entity.code if period.entity else "",
            "period": f"{period.year}-{period.month:02d}",
            "days_worked": s.days_worked or "",
            "hours_worked": float(s.hours_worked or 0),
            "hours_overtime": 0,
            "days_vacation": s.days_vacation or 0,
            "days_sick": s.days_sick or 0,
            "gross_salary": gross,
            "note": s.note or "",
        })

    # Write CSV
    export_dir = "/config/nexus/exports"
    os.makedirs(export_dir, exist_ok=True)
    fname = f"payroll_{period.year}_{period.month:02d}_{period.entity.code if period.entity else 'ALL'}.csv"
    fpath = f"{export_dir}/{fname}"
    with open(fpath, "w", newline="", encoding="utf-8-sig") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)

    batch = PayrollExportBatch(
        period_id=period_id,
        entity_id=period.entity_id,
        exported_by_id=actor_id,
        file_path=fpath,
        row_count=len(rows),
        total_gross_kc=total_gross,
    )
    db.add(batch)
    audit(db, "EXPORT", "payroll_export_batch", period_id, actor_id, actor_email,
          entity_id=period.entity_id, detail=f"rows={len(rows)} total={total_gross:.0f} Kč → {fname}")
    db.commit()
    db.refresh(batch)
    return batch
