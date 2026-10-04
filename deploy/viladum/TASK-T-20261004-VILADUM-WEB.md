# T-20261004-VILADUM-WEB

Cíl: nasadit přiložený web a PDF na fortress. Autorizace: Honza výslovně požádal o ZIP pro Claude Code, aby jej nasadil. DNS je již hotové. Před nasazením dne 4. 10. 2026 vracely kořen i `/brozura.pdf` HTTP 404.

## 1. Ověř balíček a přístup z Macu

Rozbal ZIP do samostatného místního adresáře, přečti `CLAUDE.md` a spusť:

```bash
python3 scripts/verify.py --bundle
ssh -o BatchMode=yes fortress 'hostname; df -h; docker ps --format "{{.Names}} {{.Ports}}"'
```

Hotové soubory v `public/` použij přímo. Neinstaluj build prostředí na produkční server. SSH přístup řeš běžnou existující konfigurací na Macu; žádné tokeny ani hesla v tomto balíčku nejsou.

Kontrolní bod: platné hashe a dostupný správný fortress. Balíček zabere méně než 100 MB po rozbalení; skutečnou volnou kapacitu přesto zkontroluj.

## 2. Najdi skutečný origin a vhost

Přes SSH zjisti image, porty a mounty kontejneru `investimenti-root` (jen vybraná pole `docker inspect`, nevypisuj environment s tajemstvími). Pokud je nginx jinde, použij skutečnou službu. Přečti aktivní nginx konfiguraci a zjisti:

- která služba a listener obsluhují wildcard `*.investimenti.cz`;
- kde je zahrnutá konfigurace vhostů a její hostitelský bind mount;
- který existující mount dovoluje vytvořit oddělený adresář `viladum` viditelný nginxu;
- zda je Cloudflare origin přes HTTP nebo HTTPS a jaké existující certifikáty používá.

Pokud už existuje přesný vhost pro `viladum.investimenti.cz`, aktualizuj jeho konkrétní konfiguraci a nevytvářej druhý se stejným názvem. Cizí routy, přístupové politiky a ostatní služby neměň. DNS se nemění.

Kontrolní bod: znáš skutečné hostitelské a kontejnerové cesty, origin port a TLS. Žádné cesty v příkladech nepřebírej bez ověření.

## 3. Připrav izolované nasazení

Zvol prázdný vlastní podadresář `viladum` v existujícím statickém mountu. Nginx musí vidět celý adresář se strukturou `releases/` a relativním symlinkem `current`; nemountuj samotný `current`.

Použij `deploy.sh --dry-run` se skutečnými parametry. Příklad syntaxe (hodnoty nahraď zjištěnými cestami):

```bash
bash deploy.sh --ssh fortress --sudo \
  --root /OVERENY_HOST_MOUNT/viladum \
  --nginx-root /OVERENY_CONTAINER_MOUNT/viladum \
  --mode container --container investimenti-root \
  --nginx-conf /OVERENY_HOST_CONF_MOUNT/viladum.conf \
  --listen 80 --dry-run
```

Při origin HTTPS přidej například `--listen 443 --tls-cert /SKUTECNA_CESTA_CERTIFIKATU --tls-key /SKUTECNA_CESTA_KLICE`; použij cestu viditelnou procesem nginx a zachovej další potřebné TLS nastavení ze stávající konfigurace. Při jiném listeneru použij skutečný port. Pokud origin vyžaduje oboustranné TLS nebo další existující pravidla, přenes je pouze do tohoto vhostu před regenerací manifestu. Návratové skripty neřeší odlišný globální TLS setup automaticky.

`--mode host` používá hostitelský nginx. `--mode files` kopíruje pouze veřejný obsah a vhost neupravuje; použij ho, pokud doménový blok přizpůsobíš ručně konkrétní infrastruktuře. V tomto režimu si sám zazálohuj původní vhost a ověř test/reload.

Kontrolní bod: přesný hostname, správný webroot, žádný login. Zachovej připravené MIME typy a URL `/brozura.pdf`. Ulož stav dotčené konfigurace pro rollback.

## 4. Nasaď

Spusť ověřený příkaz bez `--dry-run`. Skript přenese balíček přímo přes SSH, ověří hashe, zkopíruje jen `public/`, vytvoří nový release, přepne `current`, otestuje nginx a provede reload. Při chybě testu/reloadu obnoví předchozí vhost a symlink. Zálohy i předchozí releasy ponechá.

Pokud provozní konfigurace vyžaduje jiné začlenění vhostu, proveď odpovídající úpravu pouze pro Viladům a zachovej stejný postup testu a návratu. Nespouštěj žádný celoplošný restart ostatních kontejnerů. Nevydávej úspěšný reload za hotové veřejné nasazení.

Kontrolní bod: obsah v přesném webrootu, platný nginx, běžící správná služba.

## 5. Ověř veřejný výsledek a tisk

Na Macu z adresáře balíčku spusť:

```bash
bash verify.sh --live
```

Skript neobchází TLS a nepřijímá přesměrování. Kontroluje veřejné 200, obsah stránky a všech šest bytových sekcí, PDF podle hashe, dostupnost použitých místních assetů, adresu, 27 stran PDF, aktivní odkazy a QR skutečně dekódovaný z kontaktní strany právě stažené brožury. Případnou změnu bytů HTML při doručení přes CDN uvede v reportu; nerozhoduje o funkčnosti stránky jen podle jejího hashe.

Prohlédni desktop a mobil v běžném anonymním prohlížeči: titulní skutečnou fotografii, filtr bytů, všech šest půdorysů, zvětšení výkresu, kontakty a stažení PDF. QR musí vést na `https://viladum.investimenti.cz/` (bez koncového lomítka je stejná adresa). PDF tiskni až po této kontrole. Neprohlašuj QR za ověřený jen podle textového odkazu nebo zdrojového skriptu.

Při selhání oprav příčinu v rámci této domény a kontrolu zopakuj. Při poškození služby obnov poslední známý dobrý vhost a `current` ze zaznamenané zálohy; potom test a reload. Zálohy nepromazávej.

## 6. Jeden report

Na závěr vrať pouze:

1. Web: URL, HTTP status, veřejný přístup bez přihlášení.
2. PDF: URL, HTTP status, 27 stran a skutečná velikost.
3. QR: skutečně dekódovaná adresa, shoda s webem.
4. Provedené změny: host/container, doménový vhost, webroot a umístění zálohy.
5. Případný konkrétní blokátor. Při neověřené kontrole nesděluj, že je hotovo nebo připraveno k tisku.
