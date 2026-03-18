"""NEXUS People Calendar — narozeniny, jmeniny, výročí, firemní události."""
import os
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import extract
from backend.core.models.base import get_db
from backend.core.models.kernel import Person, Entity
from backend.core.security.auth import get_current_user, CurrentUser
from backend.core.audit.log import audit
from .calendar_models import PersonCalendarEvent, HoldingCalendarEvent, CzechNameDay

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "../../..", "frontend", "templates")
)
router = APIRouter(tags=["calendar"])


def _ctx(d):
    d.setdefault("now_date", date.today().isoformat())
    d.setdefault("active_section", "calendar")
    d.setdefault("today", date.today())
    return d


def _upcoming(db: Session, days_ahead: int = 30):
    """Get all upcoming events in next N days, handling year boundary."""
    today = date.today()
    results = []

    # Person events — birthdays, namedays, anniversaries
    person_events = db.query(PersonCalendarEvent).filter(
        PersonCalendarEvent.is_active == True
    ).all()

    for ev in person_events:
        # Find next occurrence
        for year_offset in [0, 1]:
            try:
                year = today.year + year_offset
                ev_date = date(year, ev.month, ev.day)
                delta = (ev_date - today).days
                if 0 <= delta <= days_ahead:
                    p = db.query(Person).filter(Person.id == ev.person_id).first()
                    years = (year - ev.year) if ev.year else None
                    results.append({
                        "event_type": ev.event_type,
                        "date": ev_date,
                        "delta": delta,
                        "label": ev.label or (p.full_name if p else ""),
                        "person": p,
                        "years": years,
                        "entity": db.query(Entity).filter(Entity.id == ev.entity_id).first() if ev.entity_id else None,
                        "source": "person",
                    })
                    break
            except ValueError:
                pass

    # Holding events
    holding_events = db.query(HoldingCalendarEvent).filter(
        HoldingCalendarEvent.is_active == True
    ).all()
    for ev in holding_events:
        try:
            ev_date = date.fromisoformat(ev.event_date)
            if ev.recurrence == "yearly":
                ev_date = ev_date.replace(year=today.year)
                if ev_date < today:
                    ev_date = ev_date.replace(year=today.year + 1)
            delta = (ev_date - today).days
            if 0 <= delta <= days_ahead:
                results.append({
                    "event_type": ev.event_type,
                    "date": ev_date,
                    "delta": delta,
                    "label": ev.title,
                    "person": None,
                    "years": None,
                    "entity": db.query(Entity).filter(Entity.id == ev.entity_id).first() if ev.entity_id else None,
                    "source": "holding",
                })
        except: pass

    results.sort(key=lambda x: x["date"])
    return results


# ── CALENDAR MAIN VIEW ────────────────────────────────────────────────
@router.get("/calendar", response_class=HTMLResponse)
def calendar_view(request: Request,
                  month: int = None, year: int = None,
                  type_filter: str = None,
                  db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    today = date.today()
    view_month = month or today.month
    view_year  = year  or today.year

    # Build month grid — all events this month
    all_person_events = db.query(PersonCalendarEvent).filter(
        PersonCalendarEvent.is_active == True,
        PersonCalendarEvent.month == view_month,
    ).all()
    all_holding_events = db.query(HoldingCalendarEvent).filter(
        HoldingCalendarEvent.is_active == True,
    ).all()

    month_events = []
    for ev in all_person_events:
        if type_filter and ev.event_type != type_filter:
            continue
        p = db.query(Person).filter(Person.id == ev.person_id).first()
        years = (view_year - ev.year) if ev.year else None
        month_events.append({
            "day": ev.day, "month": ev.month,
            "event_type": ev.event_type,
            "label": ev.label or (p.full_name if p else ""),
            "person": p, "years": years,
        })
    for ev in all_holding_events:
        try:
            ev_date = date.fromisoformat(ev.event_date)
            if ev.recurrence == "yearly":
                ev_date = ev_date.replace(year=view_year)
            if ev_date.month == view_month and ev_date.year == view_year:
                if type_filter and ev.event_type != type_filter:
                    continue
                month_events.append({
                    "day": ev_date.day, "month": ev_date.month,
                    "event_type": ev.event_type,
                    "label": ev.title,
                    "person": None, "years": None,
                })
        except: pass

    month_events.sort(key=lambda x: x["day"])

    # Upcoming 30 days
    upcoming = _upcoming(db, days_ahead=30)

    # Today's events
    today_events = [e for e in upcoming if e["delta"] == 0]

    # Summary counts
    birthdays_this_month = len([e for e in month_events if e["event_type"] == "birthday"])
    namedays_this_month  = len([e for e in month_events if e["event_type"] == "nameday"])
    anniversaries_this_month = len([e for e in month_events if e["event_type"] == "work_anniversary"])

    # Month name CZ
    months_cz = ['','Leden','Únor','Březen','Duben','Květen','Červen',
                  'Červenec','Srpen','Září','Říjen','Listopad','Prosinec']

    entities = db.query(Entity).filter(Entity.is_active == True).order_by(Entity.code).all()

    return templates.TemplateResponse("pages/calendar/calendar.html", _ctx({
        "request": request, "current_user": cu,
        "view_month": view_month, "view_year": view_year,
        "month_name": months_cz[view_month],
        "month_events": month_events,
        "upcoming": upcoming,
        "today_events": today_events,
        "birthdays_this_month": birthdays_this_month,
        "namedays_this_month": namedays_this_month,
        "anniversaries_this_month": anniversaries_this_month,
        "type_filter": type_filter or "",
        "entities": entities,
    }))


# ── ADD HOLDING EVENT ─────────────────────────────────────────────────
@router.post("/calendar/event/new")
def create_holding_event(
    title: str = Form(...), event_type: str = Form("company"),
    event_date: str = Form(...), end_date: str = Form(None),
    recurrence: str = Form("none"), description: str = Form(None),
    entity_id: str = Form(None), notify_days_before: int = Form(0),
    db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)
):
    ev = HoldingCalendarEvent(
        title=title, event_type=event_type,
        event_date=event_date, end_date=end_date or None,
        recurrence=recurrence, description=description,
        entity_id=entity_id or None,
        notify_days_before=notify_days_before,
        created_by=cu.email,
    )
    db.add(ev); db.commit()
    audit(db, "CREATE", "holding_calendar_event", ev.id, cu.id, cu.email, detail=f"{event_type}: {title}")
    return RedirectResponse("/calendar", status_code=303)


# ── NAMEDAY LOOKUP ────────────────────────────────────────────────────
@router.get("/calendar/namedays/today")
def today_namedays(db: Session = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    today = date.today()
    names = db.query(CzechNameDay).filter(
        CzechNameDay.day == today.day,
        CzechNameDay.month == today.month,
    ).all()
    return {"date": today.isoformat(), "names": [n.name for n in names]}
