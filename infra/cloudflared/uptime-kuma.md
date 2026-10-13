# Uptime Kuma (fortress, kontejner elias-uptime-kuma-1) – monitory tunelu

| monitor | URL | interval | OK | alert |
|---|---|---|---|---|
| citoliby | https://citoliby.investimenti.cz/ | 60 s | 200–399 (302 = Cloudflare Access login je OK) | Telegram Honza, po 2 selháních |
| citoliby-data | https://citoliby-data.investimenti.cz/ | 60 s | 200–399 | dtto |
| citoliby-archiv | https://citoliby-archiv.investimenti.cz/ | 60 s | 200–399 | dtto |

530 = Error 1033 (connector není), 52x = origin na Macu. Oba stavy alert.
Watchdog na Macu (`cz.investimenti.tunnel-watchdog`) se o restart pokusí sám do 2 minut; Kuma hlásí, když to nepomohlo.
