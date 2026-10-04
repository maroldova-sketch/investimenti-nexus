"""Shared evidence-backed content for web and PDF. Geometry and areas stay unchanged."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT.parent / 'public'
UNITS = json.loads((ROOT / 'units.json').read_text())
SITE_URL = 'https://viladum.investimenti.cz'
PROJECT_ADDRESS = 'Osvoboditelů 497, Louny'
VERIFIED = '4. 10. 2026'
EMAIL = 'j.caka@vzc.cz'
PHONE = '+420 774 320 438'
MAIN_LINE = 'Historie v architektuře. Prostor pro váš život.'
CHARACTERS = {
 'A': ('Prostor pro společný život.', 'Obytný prostor 36,30 m² propojuje vaření, stolování a odpočinek. Dvě samostatné místnosti dávají prostor ložnici a dalšímu pokoji; předsíň doplňuje šatna a oddělené WC.', [('36,30','m² obytného prostoru'),('2','samostatné pokoje'),('3+kk','dispozice')]),
 'B': ('Místo pro každého.', 'Tři samostatné pokoje a obytný prostor 34,40 m². Dispozice nabízí možnost oddělit práci, soukromí a společný čas. Chodba se šatnou, koupelna a samostatné WC doplňují každodenní zázemí.', [('3','samostatné pokoje'),('34,40','m² obytného prostoru'),('4+kk','dispozice')]),
 'C': ('Tři pokoje. Vlastní rytmus.', 'Obytný prostor 29,40 m² doplňují dvě samostatné místnosti o 19,30 a 12,60 m². Předsíň, chodba a šatna tvoří praktický přechod mezi společnou a soukromou částí bytu.', [('19,30','m² dalšího pokoje'),('2','samostatné pokoje'),('3+kk','dispozice')]),
 'D': ('Domov ve dvou úrovních.', 'Obytný prostor 35,90 m² a ložnici 21,10 m² doplňuje loft 24,55 m². Podkroví nabízí hlavní obytnou úroveň a otevřené patro nad ní.', [('24,55','m² loftu dle projektu'),('21,10','m² ložnice'),('2','úrovně bydlení')]),
 'E': ('Velkorysost bez kompromisu.', 'Největší projektová výměra v domě. Obytný prostor 57,25 m² doplňuje ložnice 26,80 m² a loft 20,30 m². Výrazná podkrovní dispozice nechává vyniknout společnému prostoru.', [('57,25','m² obytného prostoru'),('26,80','m² ložnice'),('20,30','m² loftu dle projektu')]),
 'F': ('Tři pokoje pod střechou.', 'Obytný prostor 44,00 m² tvoří hlavní místo pro společný život. Ložnice 24,10 m² a pokoj 18,50 m² přidávají soukromí. Podkrovní 3+kk s oddělenou koupelnou a WC.', [('44,00','m² obytného prostoru'),('24,10','m² ložnice'),('3+kk','dispozice')]),
}
STORY = 'Z bývalé školní budovy vznikl návrh šesti osobitých bytů. Architektonický koncept Ateliéru Jakub Jaroš propojuje charakter historického domu s velkorysými obytnými prostory.'
SECOND = 'Ve druhém nadzemním podlaží pracuje návrh s vysokými stropy, historickými okny a klidným skandinávským pojetím interiérů.'
ATTIC = 'Podkrovní koncept spojuje prvky krovu, střešní světlo a industriální materiály. Byty D a E doplňuje loftové patro; byt F nabízí dispozici 3+kk.'
GARDEN = 'Původní projekt počítá se společnou zahradou vnitrobloku, parkováním a střešní terasou. Krajinářský návrh ukazuje propojení zeleně, pobytových míst a přístupu k domu.'
GARDEN_NOTE = 'Situace a zahrada jsou projektový návrh. Konkrétní provedení a podmínky užívání sdělí kontakt projektu.'
RECONSTRUCTION = 'Proměna domu vychází z architektonického návrhu přestavby na šest bytů. Na prohlídce si projdete konkrétní jednotku i společné části a získáte informace o aktuálním stavu, standardu a termínu předání.'
AREA_NOTE = 'Výměry jsou uvedeny celkem dle původní projektové brožury. Materiálové půdorysy a interiéry představují návrh vybavení.'
LOFT_NOTE = 'Loft je součástí uvedeného projektového součtu. Řez zachycuje výškové uspořádání; přesné započítání ploch a využití pod šikminami upřesní dokumentace jednotky.'
D7_NOW = 'Obchvat Loun v širším dálničním profilu slouží od září 2023, úsek u Chlumčan od června 2024. V září 2026 ŘSD převedlo dopravu na část nového pásu u Knovíze; v této etapě zůstává režim 1+1.'
D7_FUTURE = 'Oficiální přehled plánuje dokončení úseků Knovíz–Slaný-západ, Slaný-západ–Kutrovice a Kutrovice–Panenský Týnec na rok 2027. Jde o plánovaný termín, který se může změnit.'
PID_TEXT = 'Linka PID 389 propojuje Louny se Slaným a pražským Nádražím Veleslavín. Konkrétní spoj a dobu cesty vyberte v aktuálním jízdním řádu.'
SOURCES = [
 ('Původní projektová brožura','https://drive.google.com/file/d/1PJtWO6W6cxV1JT4M3v6-jz6TvyEq-I92/view'),
 ('Ateliér Jakub Jaroš / koncept domu','https://jjarch.cz/projects-files/vzahradach/vzahradach'),
 ('D7 / oficiální přehled úseků','https://www.dalnice-d7.cz/'),
 ('ŘSD / stav k 1. 9. 2026','https://kraje.rsd.cz/stredocesky/blog/2026/09/01/na-d7-u-knovize-se-zacina-jezdit-po-prvni-casti-nove-dalnice/'),
 ('PID / regionální linky','https://pid.cz/jizdni-rady-podle-linek/autobusy-primestske/'),
 ('Město Louny / investiční plán 2026','https://www.mulouny.cz/cs/mesto/vedeni/aktualni-informace/investice-pro-budoucnost-zastupitelstvo-mesta-louny-schvalilo-rozpocetpro-rok-2026-s-vysokymi-inves.html'),
 ('Městské informační centrum / město','https://www.louny.eu/'),
 ('MIC / památky a Masarykovy sady','https://www.louny.eu/cz/louny-pamatky/573/'),
 ('MIC / cykloturistika','https://www.louny.eu/cz/cykloturistika-v-okoli-mesta-louny/389/'),
 ('Městská plavecká hala','https://www.bazenlouny.cz/plavecka-hala-louny/'),
 ('Galerie Benedikta Rejta','https://www.gbr.cz/'),
 ('Vrchlického divadlo','https://www.divadlolouny.cz/?s=homepage'),
 ('Kino Svět','https://www.kinolouny.cz/'),
 ('Městská knihovna Louny','https://www.mkl.cz/knihovna'),
 ('Triangle / pracovní zázemí','https://www.industrialzonetriangle.com/cz/pro-investory/nejcasteji-kladene-otazky'),
]
PLACES = [
 ('01','Galerie Benedikta Rejta','Umění v centru města. Pivovarská 34.','https://www.gbr.cz/','Galerie Benedikta Rejta Louny'),
 ('02','Vrchlického divadlo','Divadlo, koncerty a program pro rodiny.','https://www.divadlolouny.cz/?s=homepage','Vrchlického divadlo Louny'),
 ('03','Kino Svět','Filmový večer ve městě, s moderním obrazem a zvukem.','https://www.kinolouny.cz/','Kino Svět Louny'),
 ('04','Plavecká hala','Plavání a relaxace. Pod Nemocnicí 3125.','https://www.bazenlouny.cz/plavecka-hala-louny/','Pod Nemocnicí 3125 Louny'),
 ('05','Knihovna & kavárna','Knihy, dětské oddělení a kavárna Jeroným.','https://www.mkl.cz/knihovna','Městská knihovna Louny'),
 ('06','Masarykovy sady & Ohře','Procházky městem a zelení podél řeky.','https://www.louny.eu/cz/louny-pamatky/573/','Masarykovy sady Louny'),
]
FAQ = [
 ('Jak zjistím cenu a dostupnost?','Vyberte byt a ozvěte se Janu Čákovi. Získáte aktuální nabídku a možnost domluvit prohlídku.'),
 ('Co zahrnuje uvedená výměra?','Jde o součet místností dle projektové brožury. U bytů D a E je v součtu i loft. Právní vymezení ploch a výškové poměry ověříte v dokumentaci konkrétní jednotky.'),
 ('Je vyobrazený nábytek součástí nabídky?','Interiéry a materiálové půdorysy představují návrh vybavení. Rozsah dodávky a konkrétní standard vám potvrdí kontakt projektu.'),
 ('Jak je řešena zahrada, terasa a parkování?','Původní projekt s nimi počítá. Současné provedení, přístup a podmínky užívání projdete společně s nabídkou vybraného bytu.'),
 ('Jak probíhá další postup?','Nejprve vyberete byt, získáte aktuální nabídku a domluvíte prohlídku. Následuje projití standardu, podkladů a případných smluvních kroků podle individuální nabídky.'),
]
PENDING = [
 'Přesný vstup domu, parcelní čísla a dokumentace jednotek. Adresu Osvoboditelů 497, Louny potvrdil investor 4. 10. 2026.',
 'Plocha a hranice zahrady, současné provedení a fotografie, užívání a údržba.',
 'Terasa: realizace, poloha, plocha, přístup a užívání.',
 'Parkování: počet, přiřazení, právní režim a zahrnutí do ceny.',
 'Rozsah a stav rekonstrukce, etapizace, změna užívání/kolaudace, předání.',
 'Střecha/krov, fasáda, okna, sanace, instalace, vytápění, ohřev vody, větrání a akustika.',
 'Dodávané podlahy, dveře, koupelny a kuchyně, společné prostory, sklepy a případný výtah.',
 'PENB, provozní náklady, záruky, aktuální ceny a dostupnost.',
 'Revize bytu E: původní tabulka uvádí 3.06 koupelna / 3.07 ložnice, výkres tato čísla prohazuje. Zachováno dle zdroje; nutno potvrdit projektantem.',
]
