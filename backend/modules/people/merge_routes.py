"""
Wave 3.4 — People Merge UI
/people/merge          — list potential duplicate pairs
/people/merge/{a}/{b}  — side-by-side comparison + merge form
POST /people/merge/execute — execute merge (keep one, deactivate other)
"""
import os, json, uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.core.models.base import get_db
from backend.core.models.kernel import Person, AuditLog
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(prefix="/people", tags=["people-merge"])


def _ctx(d):
    d.setdefault("active_section", "people")
    return d


def _find_candidates(db: Session):
    """Find potential duplicate pairs by name similarity."""
    from collections import defaultdict
    active = db.query(Person).filter(Person.is_active == True).all()

    # Group by (last_name, first_name) normalized
    name_groups = defaultdict(list)
    for p in active:
        key = (
            (p.last_name or "").strip().lower(),
            (p.first_name or "").strip().lower(),
        )
        if key[0]:
            name_groups[key].append(p)

    pairs = []
    seen = set()
    for key, persons in name_groups.items():
        if len(persons) > 1:
            for i in range(len(persons)):
                for j in range(i + 1, len(persons)):
                    a, b = persons[i], persons[j]
                    pair_key = tuple(sorted([a.id, b.id]))
                    if pair_key not in seen:
                        seen.add(pair_key)
                        # Score similarity
                        score = 0
                        if a.rod_cislo and b.rod_cislo and a.rod_cislo == b.rod_cislo:
                            score += 50
                        if a.phone and b.phone and a.phone == b.phone:
                            score += 30
                        if a.email_personal and b.email_personal and a.email_personal == b.email_personal:
                            score += 30
                        if a.email_work and b.email_work and a.email_work == b.email_work:
                            score += 20
                        # Same name = base score
                        score += 20
                        pairs.append({
                            "a": a, "b": b,
                            "score": score,
                            "reasons": _diff_reasons(a, b),
                        })

    pairs.sort(key=lambda x: -x["score"])
    return pairs


def _diff_reasons(a: Person, b: Person) -> list:
    reasons = []
    if a.rod_cislo and b.rod_cislo:
        if a.rod_cislo == b.rod_cislo:
            reasons.append("stejné RČ")
        else:
            reasons.append(f"různé RČ: {a.rod_cislo} vs {b.rod_cislo}")
    if a.phone and b.phone and a.phone == b.phone:
        reasons.append("stejný telefon")
    if a.email_personal and b.email_personal:
        if a.email_personal == b.email_personal:
            reasons.append("stejný osobní email")
    if a.source_holding and b.source_holding and a.source_holding != b.source_holding:
        reasons.append(f"různý zdroj: {a.source_holding} vs {b.source_holding}")
    if not a.rod_cislo and not a.source_holding:
        reasons.append("záznam A bez RČ/zdroje — pravděpodobně starý seed")
    if not b.rod_cislo and not b.source_holding:
        reasons.append("záznam B bez RČ/zdroje — pravděpodobně starý seed")
    return reasons


PERSON_FIELDS = [
    ("Jméno", "first_name"), ("Příjmení", "last_name"), ("Rodné příjmení", "maiden_name"),
    ("Titul", "title_before"), ("Rodné číslo", "rod_cislo"), ("Datum nar.", "birth_date"),
    ("Místo nar.", "birth_place"), ("Telefon", "phone"), ("Email osobní", "email_personal"),
    ("Email pracovní", "email_work"), ("Adresa", "address_permanent"),
    ("Státní přísl.", "nationality"), ("Pracovní pozice", "position"),
    ("Oddělení", "department"), ("Datum nástupu", "hire_date"),
    ("Místo výkonu", "work_location"), ("Typ PP", "employment_type"),
    ("Zdroj holdingu", "source_holding"), ("Číslo účtu", "bank_account"),
    ("Zdravotní poj.", "health_insurance"),
]


@router.get("/merge", response_class=HTMLResponse)
def merge_list(request: Request, db: Session = Depends(get_db),
               cu: CurrentUser = Depends(get_current_user)):
    candidates = _find_candidates(db)
    return templates.TemplateResponse("pages/people/merge_list.html", _ctx({
        "request": request, "current_user": cu,
        "candidates": candidates,
        "total": len(candidates),
    }))


@router.get("/merge/{id_a}/{id_b}", response_class=HTMLResponse)
def merge_detail(id_a: str, id_b: str, request: Request,
                 db: Session = Depends(get_db),
                 cu: CurrentUser = Depends(get_current_user)):
    a = db.query(Person).filter(Person.id == id_a).first()
    b = db.query(Person).filter(Person.id == id_b).first()
    if not a or not b:
        return RedirectResponse("/people/merge")

    # Build field comparison
    fields = []
    for label, attr in PERSON_FIELDS:
        va = str(getattr(a, attr, "") or "")
        vb = str(getattr(b, attr, "") or "")
        fields.append({
            "label": label, "attr": attr,
            "val_a": va, "val_b": vb,
            "differ": va != vb,
            "both_empty": not va and not vb,
        })

    return templates.TemplateResponse("pages/people/merge_detail.html", _ctx({
        "request": request, "current_user": cu,
        "a": a, "b": b, "fields": fields,
        "reasons": _diff_reasons(a, b),
    }))


@router.post("/merge/execute")
def merge_execute(
    keep_id: str = Form(...),
    discard_id: str = Form(...),
    # Field overrides: field_{attr} = "a" | "b" | custom value
    request: Request = None,
    db: Session = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user),
):
    keep = db.query(Person).filter(Person.id == keep_id).first()
    discard = db.query(Person).filter(Person.id == discard_id).first()
    if not keep or not discard:
        return RedirectResponse("/people/merge", status_code=303)

    # Apply field choices from form
    import asyncio
    form_data = {}
    # We'll handle this synchronously via a different approach
    # For now: merge strategy = keep all non-empty fields from discard into keep if keep's field is empty
    for _, attr in PERSON_FIELDS:
        keep_val = getattr(keep, attr, None)
        discard_val = getattr(discard, attr, None)
        if not keep_val and discard_val:
            try:
                setattr(keep, attr, discard_val)
            except:
                pass

    # Mark discard as inactive with note
    discard.is_active = False
    try:
        discard.notes = (discard.notes or "") + f"\n[MERGED into {keep_id} by {cu.email} on {datetime.now().date()}]"
    except:
        pass

    db.commit()
    audit(db, "MERGE", "person", keep_id, cu.id, cu.email,
          detail=f"Merged {discard_id} into {keep_id}")

    return RedirectResponse(f"/people/{keep_id}", status_code=303)
