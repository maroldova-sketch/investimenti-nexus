# citoliby-d: zabijačka checklist + state.json (2026-09-17)

Veřejný zaklikávací checklist na https://citoliby.investimenti.cz/zabijacka/ (bez basic auth, sdílený stav).
Backend žije na Macu: `~/andrew_core/sites/citoliby-d/backend.py` (launchd `cz.investimenti.citoliby.d`, port 8017).

| soubor | k čemu |
|---|---|
| `deploy_zabijacka.sh` | jednorázové nasazení na Macu: zálohy, stažení, odkaz v index_d.html, restart, ověření, git commit |
| `backend.py` | nová verze backendu (sha256 `c1e3c124…`), původní má sha256 `7f8dbdfe…` (200 řádků) |
| `apply_zabijacka.py` | stejná změna jako anchor-based patch (idempotentní), pro případ jiné výchozí verze |
| `backend.py.diff` | diff původní → nová |
| `index.html` | stránka checklistu (sha256 `dee5f5bc…`, 26725 B), zdroj dave.investimenti.cz/p/-nUT7NfwujV7HZFm_DCDjc9fcGcz4Hwx |

Nasazení na Macu (uživatel investimenti):

```
bash deploy_zabijacka.sh
```

Co změna dělá: tři routy (`GET /zabijacka/`, `GET|POST /zabijacka/state.json`, validace + atomický zápis),
prefix `/zabijacka/` přidaný do `FREE_PATH_PREFIXES` jen v procesu citoliby-d; sdílená `lib/split_brain_auth.py` se nemění.
