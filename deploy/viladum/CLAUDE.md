# Nasadit Viladům na fortress

Uživatel autorizoval nasazení tohoto balíčku na **https://viladum.investimenti.cz/**.
Proveď celý úkol podle `TASK-T-20261004-VILADUM-WEB.md` a na konci vrať jeden stručný report.

- Web a 27stránkové PDF jsou již hotové v `public/`. Neprováděj nový redesign a neměň půdorysy, výměry, čísla místností, fotografie ani marketingové údaje.
- Adresa projektu je **Osvoboditelů 497, Louny**. QR a absolutní odkazy míří na finální doménu. PDF musí být veřejné na `/brozura.pdf`.
- Wildcard DNS, Cloudflare a veřejné HTTPS podle uživatele fungují. DNS neměň, nezakládej Access login a neměň apex investimenti.cz.
- Použij existující SSH alias fortress na Macu. Neobcházej zamítnutý Elias Bridge, nepoužívej Catbox a nehledej přihlašovací tajemství v chatu.
- Fortress má kontejner `investimenti-root`; jeho nginx roli, mounty, skutečné porty a TLS ověř před změnou. Název kontejneru sám není důkaz konfigurace.
- Celý balíček nikdy nekopíruj do veřejného webrootu. Nasazuje se jen `public/`; `source/`, fonty, interní fakta, skripty a konfigurace zůstávají neveřejné.
- Použij existující mount pro izolovaný podadresář viladum. Nový mount nebo změnu Compose dělej jen pokud je nutná; zazálohuj dotčenou konfiguraci a měň pouze příslušnou službu.
- Vhost musí odpovídat přesnému hostname. Zachovej skutečné origin TLS a existující wildcard certifikát, pokud origin poslouchá přes HTTPS. Přiložená šablona není návod přepnout origin na HTTP.
- Pro aktuální autoritativní vhost konfiguraci použij lokální SSH/nginx výpis. Poznámky v chatu nenahrazují konfiguraci. Nezobrazuj privátní klíče ani tokeny v reportu.
- Úspěch potvrď až po anonymním veřejném HTTP 200 pro stránku i PDF a skutečném dekódování QR v nasazeném PDF. Pouhé `nginx -t` nebo textový URL odkaz v PDF nestačí.

Hotový obsah nepotřebuje sestavení, Node.js, účty ani externí obrázkové hosty. `rebuild.sh` je pouze pro pozdější úpravy textů; obsah i fonty jsou součástí ZIP.
