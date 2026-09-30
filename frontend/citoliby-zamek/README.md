# Zámek Cítoliby, vikýře a bod 5 Půda a ateliéry (30. 9. 2026)

Balík pro stránku obnovy zámku na citoliby.investimenti.cz (citoliby-d, port 8017 na Mac mini).
Z cloudu na Mac nejde zapisovat (Elias Bridge je jen pro čtení), proto jsou zde hotové texty a skript.

## Obsah

- `01_korekce_vikyre_2026-09-30.md`  opravená syntéza (Kunike bez počtu, Wolf tři vikýře, Losche i dvorní strana, autor Martin Tomáš Losche)
- `02_bod5_puda_ateliery.md`  nový bod 5 ve struktuře bodů 1 až 4
- `korekce_kunike.html`, `bod5_puda_ateliery.html`  totéž jako HTML fragmenty pro vložení do stránky
- `bible_citoliby_2026-09-30.jsonl`  zápis do Bible, topic citoliby
- `apply_on_mac.py`  najde stránku, zálohuje, vloží texty, zapíše changelog, Bible, health check, commit

## Postup na Macu

```
cd ~/andrew_core && git pull   # nebo zkopírovat složku frontend/citoliby-zamek z investimenti-nexus
python3 frontend/citoliby-zamek/apply_on_mac.py                     # dry run, vypíše kde text a obrázky žijí
python3 frontend/citoliby-zamek/apply_on_mac.py --apply --bible --commit
curl -s http://127.0.0.1:8017/health
curl -s http://127.0.0.1:8017/<cesta-stranky> | grep -c "Půda a ateliéry"
```

Zálohy jdou do `~/andrew_core/audits/backups/citoliby-d/2026-09-30/`. Commit jde jako elias.marold@investimenti.cz, bez push.
