"""Wave 3.3 — DB migrations for structured webhook intake."""
from sqlalchemy import text
from backend.core.models.base import engine

MIGRATIONS = [
    "ALTER TABLE intake_record ADD COLUMN source_provider TEXT",
    "ALTER TABLE intake_record ADD COLUMN source_message_id TEXT",
    "ALTER TABLE intake_record ADD COLUMN source_phone_e164 TEXT",
    "ALTER TABLE intake_record ADD COLUMN source_received_at TEXT",
    "ALTER TABLE intake_record ADD COLUMN parsed_data TEXT",
    "ALTER TABLE intake_record ADD COLUMN attachments TEXT",
    "ALTER TABLE intake_record ADD COLUMN image_analysis TEXT",
    "ALTER TABLE intake_record ADD COLUMN confidence_score REAL",
    "ALTER TABLE intake_record ADD COLUMN unresolved_reason TEXT",
    "ALTER TABLE intake_record ADD COLUMN vehicle_resolution TEXT",
    "ALTER TABLE intake_record ADD COLUMN audit_trail TEXT",
]

CREATE_LOG = """CREATE TABLE IF NOT EXISTS webhook_intake_log (
    id TEXT PRIMARY KEY,
    received_at TEXT NOT NULL,
    source_channel TEXT,
    source_provider TEXT,
    source_message_id TEXT,
    source_phone_e164 TEXT,
    intake_type TEXT,
    raw_payload TEXT,
    intake_record_id TEXT,
    resolution_status TEXT,
    created_at TEXT
)"""

def migrate(db_engine=None):
    eng = db_engine or engine
    with eng.connect() as conn:
        for sql in MIGRATIONS:
            try:
                conn.execute(text(sql)); conn.commit()
            except: pass
        conn.execute(text(CREATE_LOG)); conn.commit()
    print("webhook migrations done")
