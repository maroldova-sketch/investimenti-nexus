"""iDoklad JSON API (/api/v1/idoklad/*) — čtení faktur + sync do Fortis.

Autentizace přes API-key (ServiceToken), scopes idoklad:read / idoklad:write.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.models.base import get_db
from backend.core.audit.log import audit
from backend.core.security.service_auth import require_scope
from backend.modules.mcp_api.models import ServiceToken
from backend.integrations.idoklad import client as idoklad

router = APIRouter(prefix="/api/v1/idoklad", tags=["idoklad"])


@router.get("/ping")
def idoklad_ping(tok: ServiceToken = Depends(require_scope("idoklad:read"))):
    try:
        idoklad.ping()
        return {"ok": True}
    except idoklad.IDokladError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/invoices")
def invoices(kind: str = Query("received", pattern="^(received|issued)$"),
             pages: int = 1, page_size: int = 50,
             tok: ServiceToken = Depends(require_scope("idoklad:read"))):
    try:
        data = idoklad.fetch_normalized(kind=kind, pages=max(1, min(pages, 20)),
                                        page_size=max(1, min(page_size, 200)))
    except idoklad.IDokladError as e:
        raise HTTPException(status_code=502, detail=str(e))
    # raw ven neposíláme (může být objemné)
    for d in data:
        d.pop("raw", None)
    return {"kind": kind, "count": len(data), "invoices": data}


def _default_entity_id(db: Session) -> str | None:
    row = db.execute(text("SELECT id FROM entity WHERE is_active=1 ORDER BY code LIMIT 1")).first()
    return row[0] if row else None


@router.post("/sync")
def sync_to_fortis(kind: str = Query("received", pattern="^(received|issued)$"),
                   pages: int = 2, entity_id: str | None = None,
                   db: Session = Depends(get_db),
                   tok: ServiceToken = Depends(require_scope("idoklad:write"))):
    """Stáhne faktury z iDokladu a upsertne je do fortis_document (source_system=idoklad)."""
    from backend.modules.fortis.models import FortisDocument
    ent = entity_id or _default_entity_id(db)
    if not ent:
        raise HTTPException(status_code=409, detail="Žádná entity v DB — nelze přiřadit doklady")
    try:
        rows = idoklad.fetch_normalized(kind=kind, pages=max(1, min(pages, 20)))
    except idoklad.IDokladError as e:
        raise HTTPException(status_code=502, detail=str(e))

    created, updated = 0, 0
    for r in rows:
        if not r["source_ref"]:
            continue
        existing = db.query(FortisDocument).filter(
            FortisDocument.source_system == "idoklad",
            FortisDocument.source_ref == r["source_ref"],
        ).first()
        fields = dict(
            entity_id=ent, doc_type=r["doc_type"], source_system="idoklad",
            source_ref=r["source_ref"], doc_number=r["doc_number"],
            doc_date=r["doc_date"], due_date=r["due_date"],
            amount_gross=r["amount_gross"], amount_net=r["amount_net"],
            amount_vat=r["amount_vat"], currency=r["currency"] or "CZK",
            counterparty_name=r["counterparty_name"], counterparty_ico=r["counterparty_ico"],
        )
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            updated += 1
        else:
            db.add(FortisDocument(status="imported", **fields))
            created += 1
    db.commit()
    audit(db, action="sync", resource_type="fortis_document", user_email=f"api:{tok.name}",
          detail=f"idoklad {kind}: +{created} ~{updated}")
    return {"ok": True, "kind": kind, "created": created, "updated": updated}
