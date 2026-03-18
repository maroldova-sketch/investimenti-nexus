
import sys
sys.path.insert(0,'.')
from backend.core.models.base import SessionLocal
from backend.core.models.kernel import Person
from datetime import date
db = SessionLocal()
ins=upd=0

def pd(s):
    if not s or s=='None': return None
    try: return date.fromisoformat(s)
    except: return None
