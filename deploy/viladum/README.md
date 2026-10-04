# Viladům v zahradách - balíček pro Claude Code

**Projekt:** Osvoboditelů 497, Louny. **Cílový web:** https://viladum.investimenti.cz/.
**Veřejné PDF:** https://viladum.investimenti.cz/brozura.pdf.

Rozbal ZIP na Macu, otevři tuto složku v Claude Code a zadej:

> Přečti CLAUDE.md a proveď TASK-T-20261004-VILADUM-WEB.md. Nasaď přiložený web a PDF na fortress přes existující SSH přístup. DNS je hotové. Ověř veřejný web, stažení PDF a QR a vrať jeden report na konci.

## Co je připravené

- `public/`: kompletní hotový statický web, všechny obrázky a půdorysy, `brozura.pdf`, CSS/JS, projektová data, zdroje a veřejný ZIP technických podkladů. Nasazuje se pouze tato složka.
- `source/`: zdrojové texty a generátory webu/PDF, nezměněná data šesti bytů, původní fotografie, přibalená písma a interní ověřovací poznámky. Tato složka se nezveřejňuje.
- `nginx/`: šablona vhostu pro přesný hostname; skutečný listener, mounty a TLS doplní Claude podle konfigurace serveru.
- `deploy.sh`: nasazení přímo přes SSH, ověření hashů, samostatné releasy, zálohy a návrat při chybě nginx testu nebo reloadu.
- `verify.sh`: kontrola veřejného webu, pravého PDF, assetů a skutečné dekódování QR ze staženého PDF.
- `rebuild.sh`: volitelná pozdější obnova webu a PDF z přiložených zdrojů a assetů, bez dohledávání obrázků. Python knihovny se instalují do místního venv; produkční web je nepotřebuje.

PDF má samostatnou 27stránkovou sazbu. Adresa je doplněna na webu i v brožuře; QR, canonical, sociální odkazy a technické odkazy používají finální doménu. Dispozice, místnosti a výměry všech šesti bytů se neměnily. Neověřené dokončení rekonstrukce, rozsah zahrady, ceny a dostupnost zůstávají k potvrzení kontaktem projektu.

DNS a veřejné HTTPS již fungují podle potvrzení uživatele. Tento ZIP sám nic na serveru nenasazuje. Veřejná kontrola před nasazením 4. 10. 2026: kořen i PDF vracely 404. Lokální ověřený výsledek je zaznamenán v `LOCAL-VALIDATION.json`; veřejný výsledek musí ověřit Claude po nasazení.

Pro místní rebuild a dekódování QR použij Python 3.12 nebo novější. Jiný příkaz Pythonu lze zvolit například `VILADUM_PYTHON=python3.13 bash verify.sh --live`. Na fortress pro kopírování a kontrolu hashů stačí jeho existující Python 3; nic se na něj neinstaluje.

Základní kontrola integrity bez instalace balíčků:

```bash
python3 scripts/verify.py --bundle
```

Zdroje nasazení: oficiální dokumentace nginx https://nginx.org/en/docs/http/server_names.html a https://nginx.org/en/docs/beginners_guide.html.
