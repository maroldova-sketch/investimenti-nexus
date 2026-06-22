"""Machine access tokens (API keys) for Elias / MCP / n8n.

Token formát:  nxs_<key_id>_<secret>
  - key_id   : veřejný prefix (uložený v DB, slouží k vyhledání)
  - secret   : náhodná část, v DB jen jako hash (pbkdf2)

Scopes (CSV) řídí, co token smí:
  fleet:read  people:read  fortis:read  notify:read  notify:write
  mail:send  idoklad:read  idoklad:write  imports:run  admin

`admin` implicitně zahrnuje všechny scopes.
"""
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.models.base import Base, engine
from backend.core.models.kernel import _uuid, _now


class ServiceToken(Base):
    __tablename__ = "service_token"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    hashed_secret: Mapped[str] = mapped_column(String(200))
    scopes: Mapped[str] = mapped_column(Text, default="")     # CSV
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[str | None] = mapped_column(String(200))

    def scope_list(self) -> list[str]:
        return [s.strip() for s in (self.scopes or "").split(",") if s.strip()]

    def allows(self, scope: str) -> bool:
        scopes = self.scope_list()
        return "admin" in scopes or scope in scopes


CREATE_SQL = """CREATE TABLE IF NOT EXISTS service_token (
    id TEXT PRIMARY KEY,
    key_id TEXT UNIQUE,
    name TEXT,
    hashed_secret TEXT,
    scopes TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_by TEXT
)"""


def migrate(db_engine=None):
    eng = db_engine or engine
    with eng.connect() as conn:
        conn.execute(text(CREATE_SQL)); conn.commit()
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_service_token_key_id ON service_token(key_id)"))
            conn.commit()
        except Exception:
            pass
