"""
GOV Connector — NEXUS API routes.
On-demand access to ISDS datové schránky data.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.models.base import get_db
from backend.modules.gov.models import GovSchranka, GovMessage, GovAttachment

router = APIRouter(prefix="/gov", tags=["gov"])


@router.get("/api/schranky")
def list_schranky(db: Session = Depends(get_db)):
    """List all registered schránky with status."""
    schranky = db.query(GovSchranka).order_by(GovSchranka.name).all()
    return [
        {
            "ds_id": s.ds_id,
            "name": s.name,
            "type": s.subject_type,
            "active": s.active,
            "credentials_ok": s.credentials_ok,
            "last_poll": s.last_poll.isoformat() if s.last_poll else None,
            "last_poll_status": s.last_poll_status,
            "message_count": s.message_count or 0,
            "password_expires_at": s.password_expires_at.isoformat() if s.password_expires_at else None,
        }
        for s in schranky
    ]


@router.get("/api/messages")
def list_messages(
    ds_id: str = None,
    limit: int = 50,
    urgent_only: bool = False,
    db: Session = Depends(get_db),
):
    """List message notifications from DB (metadata only, no content)."""
    q = db.query(GovMessage).order_by(GovMessage.received_at.desc())
    if ds_id:
        q = q.filter(GovMessage.ds_id == ds_id)
    if urgent_only:
        q = q.filter(GovMessage.is_urgent == True)
    msgs = q.limit(limit).all()
    return [
        {
            "id": m.id,
            "external_id": m.external_id,
            "ds_id": m.ds_id,
            "subject": m.subject,
            "sender_name": m.sender_name,
            "received_at": m.received_at.isoformat() if m.received_at else None,
            "is_urgent": m.is_urgent,
            "deadline_type": m.deadline_type,
            "detected_deadline": m.detected_deadline.isoformat() if m.detected_deadline else None,
            "downloaded": m.downloaded,
            "alert_sent": m.alert_sent,
        }
        for m in msgs
    ]


@router.post("/api/messages/{message_id}/download")
def download_message(message_id: int, db: Session = Depends(get_db)):
    """On-demand download of a specific message (ZFO + attachments).
    This is the ONLY way content gets downloaded — never automatic.
    """
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path.home() / "andrew" / "elias" / "gov"))
    from isds_client import ISDSClient
    from pathlib import Path

    msg = db.query(GovMessage).filter_by(id=message_id).first()
    if not msg:
        raise HTTPException(404, "Message not found")

    if msg.downloaded and msg.zfo_path:
        return {"status": "already_downloaded", "zfo_path": msg.zfo_path}

    # Download via SOAP
    try:
        client = ISDSClient(msg.ds_id)
    except Exception as e:
        raise HTTPException(400, f"No valid credentials for {msg.ds_id}: {e}")

    output_dir = Path.home() / "andrew" / "data" / "gov" / msg.ds_id / "zfo"
    result = client.download_message(msg.external_id, output_dir)

    if not result.get("ok"):
        raise HTTPException(502, f"ISDS download failed: {result.get('error')}")

    # Update DB
    msg.downloaded = True
    msg.downloaded_at = datetime.now(timezone.utc)
    msg.zfo_path = result.get("zfo_path")
    db.commit()

    return {
        "status": "downloaded",
        "zfo_path": result.get("zfo_path"),
        "message_id": msg.id,
        "external_id": msg.external_id,
    }


@router.post("/api/poll")
def trigger_poll(db: Session = Depends(get_db)):
    """Manually trigger a poll of all active schránky.
    Also dispatches Teams+Planner notification for each new message.
    """
    import sys
    from datetime import datetime, timezone, timedelta
    sys.path.insert(0, str(__import__("pathlib").Path.home() / "andrew" / "elias" / "gov"))
    from isds_poller import run_once

    pre_poll_ts = datetime.now(timezone.utc) - timedelta(seconds=5)
    results = run_once()

    # Dispatch Teams+Planner pro každou novou zprávu
    try:
        from backend.core.dispatcher import dispatch_gov_message_safe
        new_msgs = (
            db.query(GovMessage)
            .filter(GovMessage.created_at >= pre_poll_ts)
            .all()
        )
        for msg in new_msgs:
            schranka = db.query(GovSchranka).filter_by(id=msg.schranka_id).first()
            dispatch_gov_message_safe(
                schranka_name=schranka.name if schranka else msg.ds_id,
                subject=msg.subject or "(bez předmětu)",
                sender=msg.sender_name or "",
                received_at=msg.delivered_at.strftime("%Y-%m-%d %H:%M") if msg.delivered_at else "",
                is_urgent=bool(getattr(msg, "is_urgent", False)),
                deadline=msg.detected_deadline.isoformat() if getattr(msg, "detected_deadline", None) else None,
                nexus_ref=f"gov_message/{msg.id}",
                nexus_link=f"http://192.168.1.43:8000/gov",
            )
    except Exception as e:
        import logging
        logging.getLogger("gov.poll").warning(f"dispatcher failed: {e}")

    return {
        "status": "ok",
        "schranky_polled": len(results),
        "new_messages": sum(r.get("new", 0) for r in results),
        "errors": sum(r.get("errors", 0) for r in results),
        "details": results,
    }
