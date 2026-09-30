#!/usr/bin/env python3
"""Zamek Citoliby, oprava syntezy vikyru a novy bod 5 Puda a ateliery.

Spoustet na Mac mini (192.168.1.43), kde zije citoliby-d a ~/projects/citoliby.
Bez parametru jen hleda a vypise plan (dry run). S --apply provede zmeny,
kazdy soubor pred editaci zalohuje do ~/andrew_core/audits/backups/citoliby-d/2026-09-30/.

  python3 apply_on_mac.py                 # dry run, jen vypis kde text a obrazky ziji
  python3 apply_on_mac.py --apply         # zaloha + editace stranky + changelog
  python3 apply_on_mac.py --apply --bible # navic zapis do ~/andrew_core/bible/*.jsonl
  python3 apply_on_mac.py --apply --commit # navic git commit v ~/andrew_core (bez push)

Vsechny texty jsou vedle skriptu (korekce_kunike.html, bod5_puda_ateliery.html,
02_bod5_puda_ateliery.md, bible_citoliby_2026-09-30.jsonl).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.request

HOME = pathlib.Path.home()
HERE = pathlib.Path(__file__).resolve().parent
DATE = "2026-09-30"
ROOTS = [
    HOME / "andrew_core" / "sites" / "citoliby-d",
    HOME / "projects" / "citoliby",
]
SKIP_DIRS = {"archive", ".git", "node_modules", ".venv", "venv", "__pycache__", "static/tabler", "_takeout_zips"}
TEXT_EXT = {".html", ".htm", ".md", ".json", ".txt", ".py", ".jinja", ".j2"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".pdf"}
NEEDLES = ["vikýř", "vikyr", "kunike", "losche", "loschy", "podklady"]
BACKUP_ROOT = HOME / "andrew_core" / "audits" / "backups" / "citoliby-d" / DATE
AUTHOR = "Elias <elias.marold@investimenti.cz>"

# fraze, ktere se skrtaji nebo nahrazuji (poradi zalezi)
REPLACEMENTS = [
    (re.compile(r"J\.\s?P\.\s?Loschy", re.I), "Martin Tomáš Losche"),
    (re.compile(r"\bLoschy\b"), "Losche"),
    (re.compile(r"řad[aeuy]\s+osmi\s+vikýř\w*", re.I), "vikýře (počet z Kunikeho nelze odečíst, opraveno 30. 9. 2026)"),
    (re.compile(r"\bosm\w*\s+vikýř\w*", re.I), "vikýře (počet nelze odečíst, opraveno 30. 9. 2026)"),
    (re.compile(r"\b8\s+vikýř\w*", re.I), "vikýře (počet nelze odečíst, opraveno 30. 9. 2026)"),
]


def skip(p: pathlib.Path) -> bool:
    s = str(p)
    return any(f"/{d}/" in s or s.endswith(f"/{d}") for d in SKIP_DIRS)


def scan():
    hits, images = [], []
    for root in ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or skip(p):
                continue
            low = p.name.lower()
            if p.suffix.lower() in IMG_EXT and any(n in low for n in NEEDLES + ["wolf", "1894", "1909", "1812", "1833"]):
                images.append(p)
                continue
            if p.suffix.lower() not in TEXT_EXT or p.stat().st_size > 5_000_000:
                continue
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            tl = t.lower()
            found = [n for n in NEEDLES if n in tl]
            if found:
                hits.append((p, found, sum(tl.count(n) for n in found)))
    return hits, images


def backup(p: pathlib.Path) -> pathlib.Path:
    rel = p.relative_to(HOME)
    dst = BACKUP_ROOT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copy2(p, dst)
    return dst


def load(name: str) -> str:
    return (HERE / name).read_text(encoding="utf-8")


PROTECT = re.compile(r"<!-- (KOREKCE|BOD 5)\b.*?<!-- /\1 -->", re.S)


def replace_outside_blocks(text: str, log: list[str]) -> str:
    """Nahrazuje fraze jen mimo uz vlozene bloky korekce a bodu 5 (idempotence)."""
    parts, last = [], 0
    for m in PROTECT.finditer(text):
        parts.append((text[last:m.start()], False))
        parts.append((m.group(0), True))
        last = m.end()
    parts.append((text[last:], False))
    out = []
    for chunk, protected in parts:
        if not protected:
            for rx, rep in REPLACEMENTS:
                chunk, n = rx.subn(rep, chunk)
                if n:
                    log.append(f"nahrazeno {n}x {rx.pattern!r}")
        out.append(chunk)
    return "".join(out)


def patch_html(text: str) -> tuple[str, list[str]]:
    log = []
    text = replace_outside_blocks(text, log)
    if 'data-corrected="2026-09-30"' not in text:
        block = load("korekce_kunike.html")
        # korekci vlozit pred prvni nadpis obsahujici Zaver (synteza), jinak pred bod 5
        m = re.search(r"<h[23][^>]*>[^<]*z[áa]v[ěe]r", text, re.I)
        if m:
            text = text[: m.start()] + block + "\n" + text[m.start():]
            log.append("korekce vlozena pred nadpis Zaver")
        else:
            text = text + "\n" + block
            log.append("korekce pripojena na konec (nadpis Zaver nenalezen, presunout rucne)")
    if 'id="bod-5-puda-a-ateliery"' not in text:
        block = load("bod5_puda_ateliery.html")
        # bod 5 za konec sekce s nadpisem 4.
        m = re.search(r"<h[23][^>]*>\s*4[\.\)]", text)
        end = None
        if m:
            close = re.compile(r"</section>|</article>|</div>", re.I)
            mm = close.search(text, m.end())
            if mm:
                end = mm.end()
        if end:
            text = text[:end] + "\n" + block + text[end:]
            log.append("bod 5 vlozen za konec bodu 4")
        else:
            for anchor in ("</main>", "</body>"):
                i = text.rfind(anchor)
                if i != -1:
                    text = text[:i] + block + "\n" + text[i:]
                    log.append(f"bod 5 vlozen pred {anchor} (bod 4 nenalezen, zkontrolovat poradi)")
                    break
            else:
                text += "\n" + block
                log.append("bod 5 pripojen na konec")
    return text, log


def patch_md(text: str) -> tuple[str, list[str]]:
    log = []
    text = replace_outside_blocks(text, log)
    if "<!-- KOREKCE" not in text:
        text += "\n\n<!-- KOREKCE md -->\n" + load("01_korekce_vikyre_2026-09-30.md") + "\n<!-- /KOREKCE -->\n"
        log.append("korekce pripojena")
    if "<!-- BOD 5" not in text:
        text += "\n\n<!-- BOD 5 md -->\n" + load("02_bod5_puda_ateliery.md") + "\n<!-- /BOD 5 -->\n"
        log.append("bod 5 pripojen")
    return text, log


def append_changelog(p: pathlib.Path, text: str) -> tuple[str, bool]:
    m = re.search(r"(<h[23][^>]*>\s*changelog[^<]*</h[23]>|^#+\s*changelog.*$)", text, re.I | re.M)
    if not m:
        return text, False
    if p.suffix.lower() in (".html", ".htm"):
        entry = ("<ul data-changelog=\"2026-09-30\"><li>30. 9. 2026 opravena syntéza vikýřů (Kunike bez počtu, Wolf tři vikýře, Losche i dvorní strana, autor Martin Tomáš Losche)</li>"
                 "<li>30. 9. 2026 přidán bod 5 Půda a ateliéry</li></ul>")
    else:
        entry = ("\n- 30. 9. 2026 opravena syntéza vikýřů (Kunike bez počtu, Wolf tři vikýře, Losche i dvorní strana, autor Martin Tomáš Losche)"
                 "\n- 30. 9. 2026 přidán bod 5 Půda a ateliéry\n")
    if "30. 9. 2026 přidán bod 5" in text:
        return text, True
    return text[: m.end()] + "\n" + entry + text[m.end():], True


def write_bible():
    bible = HOME / "andrew_core" / "bible"
    lines = [json.loads(l) for l in load("bible_citoliby_2026-09-30.jsonl").splitlines() if l.strip()]
    out = []
    for target in ("facts.jsonl", "decisions.jsonl"):
        p = bible / target
        if p.exists():
            backup(p)
        rows = [r for r in lines if (r["type"] == "decision") == (target == "decisions.jsonl")]
        existing = p.read_text(encoding="utf-8") if p.exists() else ""
        with p.open("a", encoding="utf-8") as f:
            for r in rows:
                if r["text"][:60] in existing:
                    continue
                r.setdefault("ts", dt.datetime.now().isoformat(timespec="seconds"))
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                out.append(f"{target}: {r['type']}")
    return out


def health(url="http://127.0.0.1:8017/health"):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read(300).decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--bible", action="store_true")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--only", help="omezit editaci na soubory, jejichz cesta obsahuje tento retezec")
    a = ap.parse_args()

    hits, images = scan()
    print("== TEXT (kde ziji vikyre / Kunike / Losche) ==")
    for p, found, n in sorted(hits, key=lambda x: -x[2]):
        print(f"  {p}  [{', '.join(found)}] x{n}")
    print("== OBRAZKY / PDF ==")
    for p in images:
        print(f"  {p}")
    if not hits:
        print("Zadna stranka s temito pojmy nenalezena. Nic se needituje.")
    if not a.apply:
        print("\nDry run. Pro editaci spustit s --apply (pripadne --only <cast cesty>).")
        return

    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    changed = []
    for p, found, _ in hits:
        if a.only and a.only not in str(p):
            continue
        if p.suffix.lower() not in (".html", ".htm", ".md"):
            print(f"  preskoceno (rucne): {p}")
            continue
        if not any(k in found for k in ("kunike", "losche", "loschy")):
            continue
        text = p.read_text(encoding="utf-8")
        b = backup(p)
        new, log = patch_html(text) if p.suffix.lower() != ".md" else patch_md(text)
        new, had_changelog = append_changelog(p, new)
        if new != text:
            p.write_text(new, encoding="utf-8")
            changed.append(p)
            print(f"\nEDIT {p}\n  zaloha {b}")
            for l in log:
                print(f"  {l}")
            print(f"  changelog {'zapsan' if had_changelog else 'stranka changelog nema'}")

    if a.bible:
        for l in write_bible():
            print(f"BIBLE {l}")

    st, body = health()
    print(f"\nHEALTH 8017 -> {st} {body[:120]}")

    if a.commit and changed:
        repo = HOME / "andrew_core"
        rel = [str(p.relative_to(repo)) for p in changed if repo in p.parents]
        if a.bible:
            rel += ["bible/facts.jsonl", "bible/decisions.jsonl"]
        if rel:
            subprocess.run(["git", "-C", str(repo), "add", *rel], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "--author", AUTHOR,
                            "-m", "Citoliby: oprava syntezy vikyru (Kunike bez poctu, Losche) a bod 5 Puda a ateliery"], check=True)
            print("COMMIT hotov v ~/andrew_core, bez push.")
        outside = [str(p) for p in changed if repo not in p.parents]
        if outside:
            print("Mimo andrew_core, commitnout rucne v jejich repu:", *outside, sep="\n  ")


if __name__ == "__main__":
    sys.exit(main())
