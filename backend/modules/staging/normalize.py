import re, unicodedata

def _strip_diacritics(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def normalize_name(raw: str | None) -> str | None:
    if not raw: return None
    return _strip_diacritics(re.sub(r"\s+", " ", raw.strip())).lower()

def normalize_email(raw: str | None) -> str | None:
    return raw.strip().lower() if raw else None

def normalize_phone(raw: str | None) -> str | None:
    if not raw: return None
    d = re.sub(r"[^\d+]", "", raw.strip())
    if d.startswith("+420"): d = d[4:]
    elif d.startswith("420") and len(d) == 12: d = d[3:]
    return d or None

def normalize_plate(raw: str | None) -> str | None:
    if not raw: return None
    return re.sub(r"\s+", "", raw.strip()).upper()

def normalize_company_hint(raw: str | None) -> str | None:
    if not raw: return None
    key = re.sub(r"[^A-Z0-9]", "", raw.strip().upper())
    return {"VZC":"VZC","VZCINVESTIMENTI":"VZC","INVESTIMENTI":"INV","INV":"INV",
            "LOGPACK":"LOG","LOG":"LOG","SOL":"SOL","SOLUTION":"SOL",
            "KERA":"KERA","KERADENS":"KERA","KERADENS":"KERA"}.get(key, raw.strip()[:20])

def split_name(full: str | None) -> tuple:
    if not full: return None, None, None
    s = full.strip()
    title = None
    m = re.match(r"^(MUDr\.|Mgr\.|Ing\.|JUDr\.|PhDr\.|Bc\.)\s*", s, re.IGNORECASE)
    if m: title = m.group(1); s = s[m.end():].strip()
    parts = s.split()
    if not parts: return title, None, None
    if len(parts) == 1: return title, None, parts[0]
    return title, parts[0], " ".join(parts[1:])

def mask_personal_id(raw: str | None) -> str | None:
    if not raw: return None
    c = re.sub(r"[^0-9]", "", raw)
    return (c[:6] + "****") if len(c) >= 6 else c
