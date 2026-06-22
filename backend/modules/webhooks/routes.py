"""
Wave 3.3 — Structured intake webhook endpoints.
NEXUS accepts ONLY cleaned, structured payloads from external gateway.
Raw WhatsApp/chat data must be normalized BEFORE reaching these endpoints.

POST /webhooks/intake/odometer
POST /webhooks/intake/fine
POST /webhooks/intake/claim
POST /webhooks/intake/service
POST /webhooks/intake/tires
POST /webhooks/intake/general

Each endpoint:
  1. Validates payload shape
  2. Resolves phone → person → vehicle
  3. Creates intake_record (and optionally direct canonical record)
  4. Logs provenance to webhook_intake_log
  5. Writes audit
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.models.base import get_db
from backend.core.models.kernel import AuditLog
from backend.modules.notifications.models import IntakeRecord
from .resolver import resolve_driver, normalize_phone
from .models import migrate
from backend.core.security.service_auth import verify_webhook_signature

router = APIRouter(prefix="/webhooks", tags=["webhooks"],
                   dependencies=[Depends(verify_webhook_signature)])


# ── SHARED PAYLOAD BASE ───────────────────────────────────────────────

class WebhookBase(BaseModel):
    source_channel: str = "whatsapp"
    source_provider: str = "external_gateway"
    source_message_id: Optional[str] = None
    source_phone_e164: str
    source_received_at: Optional[str] = None

    person_phone_e164: Optional[str] = None   # canonical phone if different
    person_id: Optional[str] = None            # pre-resolved by gateway
    vehicle_id: Optional[str] = None
    entity_id: Optional[str] = None

    title: str
    body: Optional[str] = ""
    parsed_data: Optional[dict] = None
    attachments: Optional[list] = None
    image_analysis: Optional[dict] = None
    confidence_score: Optional[float] = None
    unresolved_reason: Optional[str] = None


class OdometerPayload(WebhookBase):
    intake_type: str = "odometer"
    # parsed_data should contain:
    # odometer_value: int, photo_present: bool, manual_value_present: bool


class FinePayload(WebhookBase):
    intake_type: str = "fine"
    # parsed_data: fine_amount, fine_date, fine_reason, authority_name


class ClaimPayload(WebhookBase):
    intake_type: str = "claim"
    # parsed_data: incident_date, incident_type, location, claim_amount_estimate


class ServicePayload(WebhookBase):
    intake_type: str = "service"
    # parsed_data: service_type, urgency, description


class TiresPayload(WebhookBase):
    intake_type: str = "tires"
    # parsed_data: tire_request_type, urgency, description


class GeneralPayload(WebhookBase):
    intake_type: str = "general"


# ── CORE HANDLER ─────────────────────────────────────────────────────

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def handle_intake(payload: WebhookBase, db: Session) -> dict:
    """
    Core intake handler — shared by all typed endpoints.
    1. Resolve phone → person → vehicle (unless pre-resolved by gateway)
    2. Decide status: new / unresolved
    3. Create intake_record
    4. Write webhook_intake_log
    5. Auto-convert odometer if confident + resolved
    """
    phone = normalize_phone(payload.source_phone_e164)

    # Resolution: use gateway pre-resolved ids if provided, else resolve here
    if payload.person_id:
        resolution = {
            "person_id": payload.person_id,
            "vehicle_id": payload.vehicle_id,
            "entity_id": payload.entity_id,
            "vehicle_resolution": "one" if payload.vehicle_id else "none",
            "unresolved_reason": None,
        }
    else:
        resolution = resolve_driver(phone, db)

    person_id    = resolution["person_id"]
    vehicle_id   = resolution["vehicle_id"]
    entity_id    = resolution["entity_id"]
    veh_res      = resolution["vehicle_resolution"]
    unresolved   = resolution["unresolved_reason"] or payload.unresolved_reason

    # Determine intake status
    confidence = payload.confidence_score or 1.0
    if unresolved or not person_id:
        status = "unresolved"
    elif confidence < 0.7:
        status = "new"  # needs manual review
    else:
        status = "new"

    intake_id = str(uuid.uuid4())
    now = _now_iso()

    # Build audit trail
    audit_trail = [
        {"ts": now, "event": "webhook_received",
         "channel": payload.source_channel, "provider": payload.source_provider,
         "phone": phone, "vehicle_resolution": veh_res},
    ]

    # Create IntakeRecord
    record = IntakeRecord(
        id=intake_id,
        intake_type=payload.intake_type,
        entity_id=entity_id,
        vehicle_id=vehicle_id,
        person_id=person_id,
        source_channel=payload.source_channel,
        source_ref=payload.source_message_id,
        title=payload.title,
        body=payload.body or "",
        status=status,
    )
    # Set extended fields via setattr (added by migration)
    for f, v in [
        ("source_provider",    payload.source_provider),
        ("source_message_id",  payload.source_message_id),
        ("source_phone_e164",  phone),
        ("source_received_at", payload.source_received_at or now),
        ("parsed_data",        json.dumps(payload.parsed_data or {})),
        ("attachments",        json.dumps(payload.attachments or [])),
        ("image_analysis",     json.dumps(payload.image_analysis or {})),
        ("confidence_score",   confidence),
        ("unresolved_reason",  unresolved),
        ("vehicle_resolution", veh_res),
        ("audit_trail",        json.dumps(audit_trail)),
    ]:
        try: setattr(record, f, v)
        except: pass

    db.add(record)

    # Webhook log (immutable provenance)
    log_id = str(uuid.uuid4())
    db.execute(
        __import__('sqlalchemy').text("""
            INSERT INTO webhook_intake_log
            (id, received_at, source_channel, source_provider, source_message_id,
             source_phone_e164, intake_type, raw_payload, intake_record_id,
             resolution_status, created_at)
            VALUES (:id,:ra,:sc,:sp,:smi,:spe,:it,:rp,:iri,:rs,:ca)
        """),
        {
            "id": log_id,
            "ra": now,
            "sc": payload.source_channel,
            "sp": payload.source_provider,
            "smi": payload.source_message_id,
            "spe": phone,
            "it": payload.intake_type,
            "rp": payload.model_dump_json(),
            "iri": intake_id,
            "rs": status,
            "ca": now,
        }
    )

    # Audit log
    db.add(AuditLog(
        action="CREATE",
        resource_type="intake_record",
        resource_id=intake_id,
        user_id=None,
        user_email=f"webhook:{payload.source_provider}",
        detail=f"{payload.intake_type} via {payload.source_channel} | phone={phone} | res={veh_res}",
    ))

    # Auto-convert odometer if fully resolved + confident
    converted_id = None
    if (payload.intake_type == "odometer"
            and status == "new"
            and vehicle_id
            and person_id
            and confidence >= 0.85
            and payload.parsed_data
            and payload.parsed_data.get("odometer_value")):
        from backend.modules.fleet.models import OdometerReading
        odo = OdometerReading(
            id=str(uuid.uuid4()),
            vehicle_id=vehicle_id,
            recorded_by_id=person_id,
            km=int(payload.parsed_data["odometer_value"]),
            reading_date=now[:10],
            notes=f"Auto-converted from webhook | confidence={confidence} | src={payload.source_provider}",
        )
        db.add(odo)
        converted_id = odo.id
        try:
            setattr(record, "status", "converted")
            setattr(record, "converted_type", "odometer_reading")
            setattr(record, "converted_id", converted_id)
        except: pass
        audit_trail.append({"ts": _now_iso(), "event": "auto_converted", "to": "odometer_reading", "id": converted_id})
        try: setattr(record, "audit_trail", json.dumps(audit_trail))
        except: pass

    db.commit()

    return {
        "ok": True,
        "intake_id": intake_id,
        "status": status,
        "person_id": person_id,
        "vehicle_id": vehicle_id,
        "entity_id": entity_id,
        "vehicle_resolution": veh_res,
        "unresolved_reason": unresolved,
        "auto_converted": converted_id is not None,
        "converted_id": converted_id,
    }


# ── TYPED ENDPOINTS ───────────────────────────────────────────────────

@router.post("/intake/odometer")
def webhook_odometer(payload: OdometerPayload, db: Session = Depends(get_db)):
    """Structured odometer reading from external gateway (WhatsApp photo → OCR → here)."""
    return JSONResponse(handle_intake(payload, db))


@router.post("/intake/fine")
def webhook_fine(payload: FinePayload, db: Session = Depends(get_db)):
    """Structured traffic fine notification."""
    return JSONResponse(handle_intake(payload, db))


@router.post("/intake/claim")
def webhook_claim(payload: ClaimPayload, db: Session = Depends(get_db)):
    """Structured insurance claim / incident report."""
    return JSONResponse(handle_intake(payload, db))


@router.post("/intake/service")
def webhook_service(payload: ServicePayload, db: Session = Depends(get_db)):
    """Structured service request from driver."""
    return JSONResponse(handle_intake(payload, db))


@router.post("/intake/tires")
def webhook_tires(payload: TiresPayload, db: Session = Depends(get_db)):
    """Structured tire change / check request."""
    return JSONResponse(handle_intake(payload, db))


@router.post("/intake/general")
def webhook_general(payload: GeneralPayload, db: Session = Depends(get_db)):
    """Generic structured intake (fallback type)."""
    return JSONResponse(handle_intake(payload, db))


# ── CONTRACT DOC ──────────────────────────────────────────────────────

@router.get("/intake/contract")
def webhook_contract():
    """Return the webhook payload contract as JSON documentation."""
    return {
        "version": "3.3",
        "description": "NEXUS structured intake webhook contract. External gateway must clean/normalize before posting.",
        "endpoints": {
            "POST /webhooks/intake/odometer": {
                "required": ["source_phone_e164", "title"],
                "parsed_data": {"odometer_value": "int", "photo_present": "bool", "manual_value_present": "bool"},
                "auto_converts": "odometer_reading if confidence >= 0.85 and vehicle resolved",
            },
            "POST /webhooks/intake/fine": {
                "required": ["source_phone_e164", "title"],
                "parsed_data": {"fine_amount": "float", "fine_date": "str YYYY-MM-DD", "fine_reason": "str", "authority_name": "str|null"},
            },
            "POST /webhooks/intake/claim": {
                "required": ["source_phone_e164", "title"],
                "parsed_data": {"incident_date": "str", "incident_type": "str", "location": "str|null", "claim_amount_estimate": "float|null"},
            },
            "POST /webhooks/intake/service": {
                "required": ["source_phone_e164", "title"],
                "parsed_data": {"service_type": "str", "urgency": "low|medium|high", "description": "str"},
            },
            "POST /webhooks/intake/tires": {
                "required": ["source_phone_e164", "title"],
                "parsed_data": {"tire_request_type": "swap|check|new|repair", "urgency": "low|medium|high", "description": "str"},
            },
            "POST /webhooks/intake/general": {
                "required": ["source_phone_e164", "title"],
                "parsed_data": "any",
            },
        },
        "common_fields": {
            "source_channel": "whatsapp (default)",
            "source_provider": "name of external gateway",
            "source_message_id": "external message ref",
            "source_phone_e164": "E.164 phone of sender, e.g. +420777123456",
            "source_received_at": "ISO timestamp when gateway received message",
            "confidence_score": "0.0-1.0 from gateway AI/OCR",
            "attachments": "[{filename, url, mime_type, size_bytes}]",
            "image_analysis": "{raw_text, extracted_fields, model_used}",
        },
        "resolution_logic": {
            "phone_match": "person.phone normalized to E.164, exact match",
            "vehicle_resolution": "one=auto-bind, none=unresolved, ambiguous=manual review",
            "auto_convert": "odometer only, confidence>=0.85, vehicle resolved",
        },
    }
