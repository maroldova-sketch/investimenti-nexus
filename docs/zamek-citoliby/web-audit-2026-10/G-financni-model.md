# G. Finanční model (hypotézy, ne měření)

Všechna čísla jsou **předpoklady k ověření** — web dnes nemá historii prodeje. Model slouží k rozhodnutí o rozpočtu a jako kostra pro interní systém (přepsat skutečností každý měsíc).

## G1. Vstupní předpoklady (upravit podle reality)

| Parametr | Hodnota | Zdroj / poznámka |
|---|---|---|
| Kapacita hlavní hlediště | 900 | web (F) |
| VIP arkády | 60 | web (F) |
| Počet představení/koncertů sezóna 2027 | 18 (úsporná) / 24 (růstová) / 32 (ambiciózní) | **předpoklad** — potvrdit s dramaturgií |
| Průměrná cena vstupenky hlavní hlediště | 520 Kč | odhad trhu (srovnatelné letní scény 450–690 Kč) |
| Cena VIP | 1 400 Kč | předpoklad |
| Obsazenost | 40 % / 55 % / 70 % | předpoklad (nová scéna, 1. sezóna) |
| Doplňkový prodej (gastro, parkování, program) | 90 Kč / 140 Kč / 190 Kč na diváka | předpoklad |
| Svatby 2027 | 5 (limit na webu) | F |
| Průměrná tržba na svatbu (pronájem + catering, zámek) | 220 000 Kč | předpoklad; Liblice/Loučeň balíčky 13–30 tis. jen za obřad/sál + catering 600 Kč/os × 80 |
| Firemní akce 2027 | 4 / 8 / 14 | předpoklad |
| Průměrná tržba na firemní akci | 120 000 Kč | předpoklad |
| Sezónní/gastro akce 2027 (návštěvníci × útrata) | 3 000 × 250 / 6 000 × 300 / 10 000 × 350 Kč | předpoklad |
| Podíl prodejů přes vlastní web/e-mail (bez placených médií) | 35 % / 45 % / 50 % | předpoklad (databáze + SEO) |
| Podíl prodejů z placených médií | 25 % / 30 % / 35 % | předpoklad |
| Provize ticketingu | 5 % + 0 fix (GoOut typicky 5–8 %) | ověřit nabídky |

## G2. Tržby podle scénářů (sezóna 2027, Kč bez DPH, zaokrouhleno)

| Zdroj | Úsporná | Růstová | Ambiciózní |
|---|---|---|---|
| Vstupenky hlavní hlediště (představení × 900 × obsazenost × 520) | 18×900×0,40×520 = **3 369 600** | 24×900×0,55×520 = **6 177 600** | 32×900×0,70×520 = **10 483 200** |
| VIP (představení × 60 × obsazenost × 1 400) | 18×60×0,40×1 400 = 604 800 | 24×60×0,55×1 400 = 1 108 800 | 32×60×0,70×1 400 = 1 881 600 |
| Doplňkový prodej (diváci × ARPU) | 6 912 × 90 = 622 080 | 12 672 × 140 = 1 774 080 | 21 504 × 190 = 4 085 760 |
| Svatby (5 × 220 000) | 1 100 000 | 1 100 000 | 1 100 000 |
| Firemní akce (n × 120 000) | 480 000 | 960 000 | 1 680 000 |
| Sezónní/gastro akce | 750 000 | 1 800 000 | 3 500 000 |
| **Celkem tržby digitálně ovlivněné** | **6,93 mil.** | **12,92 mil.** | **22,73 mil.** |

## G3. Náklady marketingu a webu (10/2026–8/2027, 11 měsíců)

| Položka | Úsporná | Růstová | Ambiciózní |
|---|---|---|---|
| Přestavba webu (vícestránkový Next.js + CMS + ticketing integrace) jednorázově | 180 000 (interní/freelance, šablonově) | 350 000 (agentura/freelance tým, design systém) | 600 000 (agentura, EN, custom ticketing UX) |
| Fotografie + video (2 focení + sezóna) | 40 000 | 90 000 | 180 000 |
| Obsah a copy (redaktor, 90denní plán + sezóna) | 15 000/měs = 165 000 | 30 000/měs = 330 000 | 55 000/měs = 605 000 |
| SEO + GEO správa, lokální SEO, PR | 10 000/měs = 110 000 | 20 000/měs = 220 000 | 35 000/měs = 385 000 |
| PPC správa (Google, Sklik, Meta) | 8 000/měs = 88 000 | 15 000/měs = 165 000 | 25 000/měs = 275 000 |
| Média (F5) 11 měsíců + špička | 17 000×11 + 45 000 = 232 000 | 53 000×11 + 120 000 = 703 000 | 125 000×11 + 300 000 = 1 675 000 |
| Nástroje (Ecomail, GTM/GA4 0, ticketing provize 5 % z vstupenek, hosting Vercel, Windsor/dashboard) | 30 000 + provize 199 000 = 229 000 | 45 000 + 364 000 = 409 000 | 60 000 + 618 000 = 678 000 |
| Analytika a dashboard (nastavení, měsíční report) | 25 000 | 60 000 | 100 000 |
| **Celkem** | **1,07 mil.** | **2,33 mil.** | **4,50 mil.** |
| **Měsíčně (průměr)** | **~97 000** | **~212 000** | **~409 000** |
| z toho média + správa + obsah (bez jednorázových) | ~55 000/měs | ~130 000/měs | ~265 000/měs |

Doporučení v A („95 tis./měs“) = růstová varianta bez jednorázové přestavby webu a focení (ty jsou investice, ne provoz).

## G4. Návratnost (hrubě, bez provozních nákladů zámku)

| | Úsporná | Růstová | Ambiciózní |
|---|---|---|---|
| Tržby digitálně ovlivněné | 6,93 mil. | 12,92 mil. | 22,73 mil. |
| Náklady marketing + web | 1,07 mil. | 2,33 mil. | 4,50 mil. |
| Poměr tržby / marketingové náklady | 6,5× | 5,5× | 5,1× |
| Marketing jako % tržeb | 15 % | 18 % | 20 % |
| Break-even obsazenost (jen vstupenky kryjí marketing) | ~13 % | ~19 % | ~30 % |

Interpretace: i úsporná varianta se vrací, pokud sezóna 2027 reálně proběhne s ≥ 18 představeními a obsazeností ≥ 40 %. Růstová varianta má nejlepší poměr riziko/výnos: vyšší fixní obsah a web (aktiva pro 2028+) a média škálovatelná podle skutečných CPA.

## G5. Citlivostní analýza (růstová varianta)

| Změna | Dopad na tržby | Poznámka |
|---|---|---|
| Obsazenost −10 p. b. (55 → 45 %) | −1,32 mil. (vstupenky + VIP + doplňky) | nejcitlivější parametr → investovat do předprodeje a programu |
| Průměrná cena −100 Kč | −1,19 mil. | ceny držet, slevy jen early-bird/segmenty |
| Počet představení −6 | −1,77 mil. | dramaturgie = obchodní rozhodnutí |
| Doplňkový prodej −50 % | −0,89 mil. | gastro a VIP balíčky jsou „levné“ tržby |
| Svatby 5 → 3 | −0,44 mil. | ale svatební poptávky z 2027 → 2028 |
| Firemní akce 8 → 4 | −0,48 mil. | B2B kampaň září–listopad |
| CPA vstupenky 2× horší | +0,35 mil. nákladů | sledovat týdně, přesun do e-mailu/SEO |
| Spuštění webu o 2 měsíce později (únor místo prosince) | ztráta vánočního předprodeje: −0,6 až −1,0 mil. | **časový faktor je největší riziko** |

## G6. Podmínky, za kterých se investice vrátí
1. Program a ticketing live do prosince 2026 (vánoční prodej + early-bird).
2. Web s /program, /svatby, /firemni-akce a měřením do 60 dnů.
3. Měsíční kontrola CPA/ROAS a přesun rozpočtu mezi kanály (ne roční plán).
4. Databáze ≥ 3 000 kontaktů do dubna 2027 (dnes 57 → bez webu a akcí to nepůjde).
5. Upřímná komunikace stavu obnovy — jinak hrozí reputační ztráta (refundace, recenze).
