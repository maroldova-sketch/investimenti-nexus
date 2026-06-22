#!/usr/bin/env python3
"""M365 self-test — projede VŠECHNY funkce M365 modulu a vypíše PASS/FAIL.

Spouštěj na nodu, kde je nastavené .env s M365_* creds (refresh token).
Testuje reálný kód z backend/integrations/m365/client.py proti Graph API.

  python scripts/m365_selftest.py
  python scripts/m365_selftest.py --expect produkce@zamek-citoliby.cz
  python scripts/m365_selftest.py --send          # pošle i testovací e-mail (na vlastní schránku)
  python scripts/m365_selftest.py --send --to produkce@zamek-citoliby.cz

POZOR: modul používá delegovanou auth (/me/...). Aktivní schránka = vlastník
M365_REFRESH_TOKEN. --expect ověří, že je to opravdu očekávaná adresa.

Exit: 0 = vše PASS; 1 = aspoň jeden FAIL.
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GRN, YEL, RED, RST = "\033[32m", "\033[33m", "\033[31m", "\033[0m"
results: list[tuple[str, bool, str]] = []


def check(name: str, fn):
    """Spustí fn(), zaznamená PASS/FAIL a vrátí výsledek (nebo None)."""
    try:
        val = fn()
        results.append((name, True, ""))
        print(f"  {GRN}PASS{RST}  {name}")
        return val
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        results.append((name, False, msg))
        print(f"  {RED}FAIL{RST}  {name}\n        {msg[:300]}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", help="očekávaná adresa aktivní schránky (ověří se proti /me)")
    ap.add_argument("--send", action="store_true", help="otestovat i odeslání e-mailu")
    ap.add_argument("--to", help="příjemce test mailu (default = vlastní schránka)")
    args = ap.parse_args()

    print(f"════ M365 self-test @ {datetime.now():%F %T} ════\n")

    # 0) konfigurace
    from backend.config import get_settings
    s = get_settings()
    missing = [v for v in ("m365_tenant_id", "m365_client_id", "m365_client_secret", "m365_refresh_token")
               if not getattr(s, v, "")]
    if missing:
        print(f"{RED}✗ Chybí konfigurace: {', '.join(m.upper() for m in missing)}{RST}")
        print("  Nastav je v .env na tomto nodu a spusť znovu.")
        sys.exit(2)
    print(f"{GRN}✓ M365 creds přítomné{RST} (tenant={s.m365_tenant_id[:8]}…)\n")

    from backend.integrations.m365 import client as m365
    from backend.integrations.m365.auth import get_access_token

    # 1) token
    check("token: acquire_token_by_refresh_token", get_access_token)

    # 2) /me — kdo jsme + ověření očekávané schránky
    me = check("me: profil aktivní schránky", m365.me)
    active_addr = None
    if me:
        active_addr = me.get("mail") or me.get("userPrincipalName")
        print(f"        aktivní schránka: {YEL}{active_addr}{RST}")
        if args.expect:
            if (active_addr or "").lower() == args.expect.lower():
                print(f"        {GRN}✓ odpovídá --expect {args.expect}{RST}")
                results.append(("expect: schránka odpovídá", True, ""))
            else:
                print(f"        {RED}✗ NEodpovídá --expect {args.expect} "
                      f"(token patří jiné schránce!){RST}")
                results.append(("expect: schránka odpovídá", False,
                                f"aktivní={active_addr} != expect={args.expect}"))

    # 3) mail: list / search / detail
    msgs = check("mail: list_messages(inbox)", lambda: m365.list_messages(top=5))
    if msgs and msgs.get("value"):
        first_id = msgs["value"][0]["id"]
        check("mail: get_message(detail)", lambda: m365.get_message(first_id))
    else:
        print(f"  {YEL}skip{RST}  mail: get_message (prázdná schránka)")
    check("mail: search_messages", lambda: m365.search_messages("faktura", top=3))

    # 4) kalendář
    now = datetime.now(timezone.utc)
    check("calendar: list_events(±30 dní)",
          lambda: m365.list_events((now - timedelta(days=30)).isoformat(),
                                   (now + timedelta(days=30)).isoformat(), top=5))

    # 5) kontakty
    check("contacts: list_contacts", lambda: m365.list_contacts(top=5))

    # 6) soubory (OneDrive/SharePoint)
    check("files: list_drive_root", lambda: m365.list_drive_root(top=5))

    # 7) odeslání (jen s --send)
    if args.send:
        recipient = args.to or active_addr
        if not recipient:
            print(f"  {YEL}skip{RST}  mail: send (neznámý příjemce)")
        else:
            subj = f"[NEXUS self-test] {datetime.now():%F %T}"
            check(f"mail: send_mail → {recipient}",
                  lambda: m365.send_mail(recipient, subj,
                                         "<p>Automatický test z NEXUS m365_selftest. "
                                         "Pokud tohle vidíš, odesílání funguje. ✅</p>"))
    else:
        print(f"  {YEL}skip{RST}  mail: send_mail (přidej --send pro test odeslání)")

    # ── souhrn ──
    ok = sum(1 for _, p, _ in results if p)
    fail = sum(1 for _, p, _ in results if not p)
    print(f"\n──── SOUHRN: {GRN}{ok} PASS{RST}, "
          f"{(RED if fail else GRN)}{fail} FAIL{RST} ────")
    if fail:
        for name, p, msg in results:
            if not p:
                print(f"  {RED}✗{RST} {name}: {msg[:200]}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
