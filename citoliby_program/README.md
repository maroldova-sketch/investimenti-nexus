# Modul PROGRAM pro Cítoliby dashboard (index_master.html)

Zdroj pravdy pro program, ceník, lóže a kalkulaci večera je jeden soubor
`dashboard/data/program.json`. Devátý tab `program` v `index_master.html`
ho čte přes `fetch`, nic není natvrdo. Tab `kultura` zůstává beze změny.

## Obsah složky

| Soubor | K čemu |
|---|---|
| `program.json` | data: venue, ceník (5 sektorů, 902 míst), lóže (8×4 + 4×2 = 40 os, 1990 Kč), ekonomika, katalog (6 titulů Divadla Metro), kalendář (56 akcí) |
| `program_tab_section.html` | HTML sekce `#tab-program` (kalendář, ceník a kapacita, kalkulace večera) |
| `program_tab.js` | logika tabu: fetch, filtry, ceník, kalkulace, bod zvratu, chybová hláška |
| `backend_program_routes.py` | blok rout pro `~/andrew_core/sites/citoliby-d/backend.py` (`/dashboard/data/program.json`, `/api/program`, `/master`), vkládá se před catch-all `/{path:path}` |
| `deploy_program.sh` | idempotentní nasazení na Macu: zálohy `.bak.<timestamp>`, splice, restart, HTTP testy, git commit |
| `build_program.py` | generátor `program.json` (pro příští úpravy dat) |

## Nasazení na Macu (192.168.1.43)

```bash
bash /cesta/k/citoliby_program/deploy_program.sh
```

Skript udělá kroky 2 až 4 ze zadání: `program.json` na místo, tab do
`index_master.html` (nav + sekce + inline script), routy do `backend.py`
před catch-all, `launchctl kickstart -k gui/$(id -u)/cz.investimenti.citoliby.d`,
curl na `/master` a `/dashboard/data/program.json` (obojí musí být 200) a
commit v `~/castello-citoliby` pod `elias.marold@investimenti.cz`.
Před každým přepisem vzniká `.bak.<timestamp>`; nic se nemaže.
`SKIP_RESTART=1 SKIP_GIT=1` spustí jen souborovou část.

## Kalkulace večera (co počítá)

- náklady: cena zájezdu + DPH 21 %, doprava `km × 2 × 16 Kč × vozidel + čekačka × 300 Kč × vozidel`, provoz večera (předvyplněný odvozením z CFO bodu zvratu: čistá tržba při 38,8 % minus 140 000 fix minus 8 000 doprava, lze přepsat)
- tržba: sektory × obsazenost (+ přirážka prémiový večer / koncert), lóže zvlášť × obsazenost lóží
- DPH ze vstupného 12 % z hrubé tržby, autorský honorář % z hrubé tržby parteru (základ potvrdit)
- výsledek, bod zvratu v % kapacity a v hostech, porovnání s `ekonomika.break_even_obsazenost`

## Co v datech chybí (doplní Honza)

- zaměření arkád a přesná kapacita lóží (`venue.loze.poznamka`)
- km z Prahy pro Divadlo Metro (výchozí 60 km v kalkulačce je jen placeholder)
- základ pro autorský honorář (hrubá tržba parteru vs. včetně lóží)
- CFO FINAL v2 nebyl při sestavení k dispozici (viz `zdroje_poznamka` v JSON); hodnoty jsou ze zadání
- `Zamek_Citoliby_Gastro_Model_2027_RED.xlsx` v `~/Downloads` nebyl čten; gastro kalendář je z `zamecka-resonance-citoliby.html`
