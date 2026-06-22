#!/usr/bin/env python3
"""Správa NEXUS service tokenů (API-keys pro Elias / MCP / n8n).

Spouštěj na nodu s Nexusem (čte stejnou DB jako app).

  python scripts/nexus_token.py create "elias-mcp" --scopes fleet:read,fortis:read,notify:write
  python scripts/nexus_token.py create "elias-admin" --scopes admin
  python scripts/nexus_token.py list
  python scripts/nexus_token.py revoke <key_id>

POZOR: plný token (nxs_...) se vypíše JEN při create. Ulož ho hned do .env
jako NEXUS_API_KEY na straně klienta (MCP/n8n). V DB je jen hash.
"""
import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.models.base import SessionLocal
from backend.modules.mcp_api.models import ServiceToken, migrate
from backend.core.security import service_auth as sa

VALID_SCOPES = {
    "fleet:read", "people:read", "fortis:read", "notify:read", "notify:write",
    "mail:send", "idoklad:read", "idoklad:write", "imports:run", "admin",
}


def cmd_create(args):
    scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
    unknown = [s for s in scopes if s not in VALID_SCOPES]
    if unknown:
        print(f"! Neznámé scopes: {unknown}\n  Povolené: {sorted(VALID_SCOPES)}")
        sys.exit(2)
    full, key_id, secret = sa.generate_token()
    db = SessionLocal()
    try:
        tok = ServiceToken(
            key_id=key_id, name=args.name,
            hashed_secret=sa.hash_secret(secret),
            scopes=",".join(scopes), is_active=True,
            created_at=datetime.utcnow(), created_by="cli",
        )
        db.add(tok); db.commit()
    finally:
        db.close()
    print("✓ Token vytvořen. Tohle se ukáže JEN teď:\n")
    print(f"  NEXUS_API_KEY={full}\n")
    print(f"  key_id : {key_id}")
    print(f"  name   : {args.name}")
    print(f"  scopes : {','.join(scopes)}")


def cmd_list(args):
    db = SessionLocal()
    try:
        toks = db.query(ServiceToken).order_by(ServiceToken.created_at.desc()).all()
        if not toks:
            print("(žádné tokeny)"); return
        for t in toks:
            flag = "✓" if t.is_active else "✗"
            last = t.last_used_at.isoformat() if t.last_used_at else "—"
            print(f"{flag} {t.key_id}  {t.name:24}  [{t.scopes}]  last_used={last}")
    finally:
        db.close()


def cmd_revoke(args):
    db = SessionLocal()
    try:
        t = db.query(ServiceToken).filter(ServiceToken.key_id == args.key_id).first()
        if not t:
            print(f"! key_id {args.key_id} nenalezen"); sys.exit(1)
        t.is_active = False; db.commit()
        print(f"✓ Token {args.key_id} ({t.name}) deaktivován")
    finally:
        db.close()


def main():
    migrate()
    p = argparse.ArgumentParser(description="NEXUS service token správa")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create"); c.add_argument("name")
    c.add_argument("--scopes", default="notify:write",
                   help="CSV scopes nebo 'admin'")
    c.set_defaults(func=cmd_create)

    sub.add_parser("list").set_defaults(func=cmd_list)

    r = sub.add_parser("revoke"); r.add_argument("key_id")
    r.set_defaults(func=cmd_revoke)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
