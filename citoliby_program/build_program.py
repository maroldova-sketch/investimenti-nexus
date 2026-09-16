import json, datetime

K = "kandidat"
katalog = [
 {"id":"metro-hitler","typ":"divadlo","titul":"U Hitlerů v kuchyni","autor":"Arnošt Goldflam","rezie":"Luboš Balák","soubor":"Divadlo Metro",
  "obsazeni":["Petr Jeništa","Táňa Malíková / Nicole Tisotová","Filip Rajmont / Ondřej Bauer","Zuzana Kajnarová / Lucie Syrová","Jan Zadražil / Jiří Ployhar","Barbora Klepal Šampalíková / Eliška Vocelová","Kryštof Zapletal / Jan Kozák"],
  "anotace":"Šest aktovek spojených postavou Adolfa Hitlera. Černý humor.",
  "poznamka":"Kouří se, světelná pyrotechnika, vulgarismy, s přestávkou. 3 vozidla.",
  "cena":120510,"honorar_pct":12,"honorar_kdo":"AURA-PONT","vozidel":3,"stav":K},
 {"id":"metro-cviceni","typ":"divadlo","titul":"Zázračné cvičení","autor":"Daniel Glattauer","rezie":"Ondřej Zajíc","soubor":"Divadlo Metro",
  "obsazeni":["Hynek Čermák","Filip Rajmont","Jiří Hána"],
  "anotace":"Světový hit poprvé v čistě mužském obsazení se souhlasem autora.",
  "poznamka":"Tři herci, minimální scéna, technicky nejjednodušší.",
  "cena":127175,"honorar_pct":14.95,"honorar_kdo":"AURA-PONT","vozidel":2,"stav":K},
 {"id":"metro-more","typ":"divadlo","titul":"České moře aneb Královec na prvním místě","autor":"Vilém Dubnička","rezie":"Vilém Dubnička","soubor":"Divadlo Metro",
  "obsazeni":["Milan Šteindler","Michaela Badinková","Radek Valenta","Kristýna Frejová","Zdeněk Rohlíček"],
  "anotace":"Absurdní komedie o tajném projektu ministerstva vnitra. První cena v soutěži Dráma 2023.",
  "poznamka":"Pět herců, dvě dějství.",
  "cena":96810,"honorar_pct":12,"honorar_kdo":"autor Vilém Dubnička","vozidel":2,"stav":K},
 {"id":"metro-manzele","typ":"divadlo","titul":"Manželé v nesnázích","autor":"Éric Assous","rezie":"Ondřej Zajíc","soubor":"Divadlo Metro",
  "obsazeni":["Lucie Vondráčková","Jaromír Nosek"],
  "anotace":"Francouzská konverzační komedie o manželské krizi po zhlédnutí romantického filmu.",
  "poznamka":"Dva herci, komorní.",
  "cena":112715,"honorar_pct":13,"honorar_kdo":"DILIA","vozidel":2,"stav":K},
 {"id":"metro-pratelak","typ":"divadlo","titul":"Přátelák","autor":"","rezie":"","soubor":"Divadlo Metro",
  "obsazeni":["Lukáš Pečenka / Mira Nosek","Anna Grundmanová / Kateřina Marie Fialová / Lenka Zahradnická","Michal Slaný","Jitka Ježková / Malvína Pachlová","Filip Cíl"],
  "anotace":"Dva páry, grilování a žádost o dítě.",
  "poznamka":"Nejlevnější titul, mladší obsazení.",
  "cena":91915,"honorar_pct":14.8,"honorar_kdo":"AURA-PONT","vozidel":2,"stav":K},
 {"id":"metro-hedy","typ":"divadlo","titul":"Hedy!","autor":"","rezie":"Luboš Balák","soubor":"Divadlo Metro",
  "obsazeni":["Lucie Vondráčková","Filip Teller","Ondřej Kokorský","William Valerián"],
  "anotace":"Život Hedy Lamarr vyprávěný třemi klauny.",
  "poznamka":"Honorář v ceně zájezdu, z tržby neodchází žádné procento; při vyšší návštěvnosti nejvýhodnější.",
  "cena":122715,"honorar_pct":0,"honorar_kdo":"v cene zajezdu","vozidel":2,"stav":K},
]

SRC_K = "index_master.html tab kultura"
SRC_G = "zamecka-resonance-citoliby.html #gastro"
SRC_D = "zamecka-resonance-citoliby.html #leto (divadelní kalendář 2027)"

def e(id, mesic, datum, nazev, typ, rezim, tentpole, stav, poznamka, katalog_id=None):
    return {"id":id,"mesic":mesic,"datum":datum,"nazev":nazev,"typ":typ,"rezim":rezim,
            "tentpole":tentpole,"katalog_id":katalog_id,"stav":stav,"poznamka":poznamka}

P="plan"; N="navrh"
kal = [
 # LEDEN
 e("gastro-01-zabijacka-1",1,None,"Tlačenka & svařák · zabijačka I.","gastro","uvnitr",False,P,"Tříkrálová polévka, medovina. Zdroj: "+SRC_G),
 e("kult-01-zimni-zamek",1,None,"Zimní zámek: interiéry, kavárna, komorní koncerty","koncert","uvnitr",False,P,"Zdroj: "+SRC_K),
 # ÚNOR
 e("gastro-02-masopust",2,None,"Masopust & velká zabijačka II.","gastro","hybrid",True,P,"Jitrnice, jelita, prdelačka, slivovice, masky. Staročeské obyčeje s SDH. Zdroj: "+SRC_G+"; "+SRC_K),
 # BŘEZEN
 e("gastro-03-postni-stul",3,None,"Postní stůl","gastro","uvnitr",False,P,"Josefský sleď, ryby, čočka, jarní pivo. Zdroj: "+SRC_G),
 e("kult-03-bylinky",3,None,"Jarní úklid + bylinkové dílny","tradice","hybrid",False,P,"Zdroj: "+SRC_K),
 # DUBEN
 e("kult-04-velikonoce",4,None,"Velikonoce barokní","tradice","hybrid",True,P,"Velikonoční hod, vajíčkové dílny, barokní hudba z archivu zámku, otevřená kaple. Gastro: beránek, pečené sele, jidáše. Mezigenerační. Zdroj: "+SRC_K+"; "+SRC_G),
 e("kult-04-carodejnice",4,"2027-04-30","Pálení čarodějnic (Filipojakubská noc)","tradice","venku",True,P,"Spolupráce se SDH Cítoliby. Vatra v parku, průvod, hry pro děti, klobásy, opékačky. Tradice obce. Zdroj: "+SRC_K),
 # KVĚTEN
 e("gastro-05-chrest",5,None,"Chřestové slavnosti","gastro","hybrid",False,P,"Jehněčí. Zdroj: "+SRC_G),
 e("gastro-05-jahody",5,None,"Jahodový víkend","gastro","hybrid",False,P,"Zdroj: "+SRC_G),
 e("kult-05-rudolf",5,None,"Květiny pro Rudolfa","tradice","venku",False,P,"Zdroj: "+SRC_K),
 e("div-05-21-vip-preview",5,"2027-05-21","VIP preview & otevření sezóny","divadlo","hybrid",False,N,"Partneři, sekt v lóžích. Zdroj: "+SRC_D),
 e("div-05-22-signature",5,"2027-05-22","Signature: Zámek se probouzí","divadlo","venku",True,N,"Prestiž, start předprodeje. Zdroj: "+SRC_D),
 e("div-05-29-caveman",5,"2027-05-29","Caveman / vztahová komedie","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("kult-05-maje",5,"2027-05-30","Staročeské máje (SDH)","tradice","venku",False,P,"Zdroj: "+SRC_K),
 # ČERVEN
 e("div-06-04-cena-za-neznost",6,"2027-06-04","Cena za něžnost","divadlo","venku",False,N,"Stašová / Etzler. Titul nepotvrzen. Zdroj: "+SRC_D),
 e("kult-06-ruze",6,"2027-06-04","Slavnost růží","tradice","venku",True,P,"3denní festival přes 1. víkend v červnu (4.–6. 6. 2027). Růžová expozice, sazenice, kavárna, komorní koncerty. Cíl 1500 osob. Zdroj: "+SRC_K),
 e("gastro-06-ruze-bbq",6,"2027-06-04","Růže & BBQ","gastro","venku",True,P,"Rosé víno a piva, smoker, mladé brambory. Vázáno na Slavnost růží. Zdroj: "+SRC_G),
 e("div-06-05-divci-valka",6,"2027-06-05","Dívčí válka","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("div-06-11-chlap-na-zabiti",6,"2027-06-11","Chlap na zabití / Vše o mužích","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("div-06-12-sen-noci",6,"2027-06-12","Sen noci svatojánské","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("div-06-19-particka",6,"2027-06-19","Partička na vzduchu","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("kult-06-den-otcu",6,None,"Den otců na zámku","tradice","venku",False,P,"Zdroj: "+SRC_K),
 # ČERVENEC
 e("div-07-01-lotrando",7,"2027-07-01","Lotrando a Zubejda (rodinný muzikál)","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("div-07-02-particka",7,"2027-07-02","Partička na vzduchu","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("div-07-03-karlstejn-gala",7,"2027-07-03","Noc na Karlštejně / gala","divadlo","venku",False,N,"Gala lóže. Titul nepotvrzen. Zdroj: "+SRC_D),
 e("div-07-04-divci-valka",7,"2027-07-04","Dívčí válka","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("konc-07-05-hvezda",7,"2027-07-05","Koncert / hvězda (státní svátek)","koncert","venku",False,N,"Zdroj: "+SRC_D),
 e("kult-07-levandule",7,None,"Levandulové dny","tradice","venku",False,P,"Zdroj: "+SRC_K),
 e("gastro-07-rose-meloun",7,None,"Rosé festival & meloun, brunch","gastro","venku",False,P,"Zdroj: "+SRC_G),
 e("kult-07-jakub",7,"2027-07-25","Sv. Jakub pouť","tradice","venku",True,P,"Patronátní pouť. Mše v kapli, jarmark, večerní koncert v zahradě, gastro stánky lokálních producentů. Identita obce. Zdroj: "+SRC_K+"; "+SRC_G),
 # SRPEN
 e("gastro-08-chmel-pivo",8,None,"Chmel & pivo (20+ pivovarů)","gastro","venku",False,P,"Ne 1. víkend srpna: Letní lounské vábení (6 km). Zdroj: "+SRC_G),
 e("gastro-08-rajcata",8,None,"Rajčatová slavnost","gastro","venku",False,P,"Zdroj: "+SRC_G),
 e("kult-08-kino",8,None,"Letní kino","tradice","venku",False,P,"Zdroj: "+SRC_K),
 e("div-08-13-particka",8,"2027-08-13","Partička na vzduchu","divadlo","venku",False,N,"Srpen začíná až 2. víkendem (kolize Vábení Louny). Zdroj: "+SRC_D),
 e("div-08-14-karlstejn",8,"2027-08-14","Noc na Karlštejně / koncert","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("div-08-20-divci-valka-sen",8,"2027-08-20","Dívčí válka / Sen","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("konc-08-21-operetni-gala",8,"2027-08-21","Operetní gala / hvězda","koncert","venku",False,N,"Zdroj: "+SRC_D),
 e("div-08-22-matinee",8,"2027-08-22","Rodinný matinée (neděle)","divadlo","venku",False,N,"Zdroj: "+SRC_D),
 e("div-08-27-komedie",8,"2027-08-27","Komedie / Palace","divadlo","venku",False,N,"Titul nepotvrzen. Zdroj: "+SRC_D),
 e("div-08-28-finale",8,"2027-08-28","FINÁLE: Zámek se probouzí","divadlo","venku",True,N,"Zdroj: "+SRC_D),
 e("kult-08-hradozamecka-noc",8,None,"Hradozámecká noc","tradice","hybrid",False,P,"Zdroj: "+SRC_K),
 # ZÁŘÍ
 e("gastro-09-vinobrani-burcak",9,None,"Vinobraní & burčák","gastro","venku",True,P,"Vinařské víkendy (Mostecké víno). Zdroj: "+SRC_G+"; "+SRC_K),
 e("gastro-09-svestky",9,None,"Švestkové hody","gastro","hybrid",False,P,"Zdroj: "+SRC_G),
 e("gastro-09-posviceni",9,None,"Posvícenská husa","gastro","uvnitr",False,P,"Zdroj: "+SRC_G),
 e("kult-09-dozinky",9,None,"Dožínky","tradice","venku",False,P,"Dočesná Žatec 1. víkend září = kolize, září jen rezerva. Zdroj: "+SRC_K),
 # ŘÍJEN
 e("gastro-10-houby",10,None,"Houbový víkend","gastro","hybrid",False,P,"Zdroj: "+SRC_G),
 e("gastro-10-zverina",10,None,"Zvěřinové hody","gastro","uvnitr",False,P,"Tab kultura je má v listopadu, gastro rok v říjnu. Zdroj: "+SRC_G+"; "+SRC_K),
 e("gastro-10-dyne",10,None,"Dýňový víkend","gastro","hybrid",False,P,"Zdroj: "+SRC_G),
 e("kult-10-barokni-hudba",10,None,"Barokní hudba · procházky podzimní zahradou","koncert","hybrid",False,P,"Zdroj: "+SRC_K),
 # LISTOPAD
 e("gastro-11-svatomartinska",11,"2027-11-11","Svatomartinská hostina","gastro","uvnitr",True,P,"Husa, mladé víno. Zdroj: "+SRC_G+"; "+SRC_K),
 e("gastro-11-zabijacka-3",11,None,"Zabijačka III.","gastro","hybrid",False,P,"Zdroj: "+SRC_G),
 e("gastro-11-whisky",11,None,"Whisky večery","gastro","uvnitr",False,P,"Zdroj: "+SRC_G),
 # PROSINEC
 e("kult-12-advent",12,None,"Adventní zámek: 4 víkendy","tradice","hybrid",True,P,"1) advent + jarmark, 2) sv. Mikuláš, 3) vánoční hudba, 4) štědrovečerní procházka. Adventní kavárna v salónech. Kapr, vánočka. High season Q4, cca 4000 osob. Zdroj: "+SRC_K+"; "+SRC_G),
 e("kult-12-mikulas",12,"2027-12-05","Sv. Mikuláš","tradice","hybrid",False,P,"2. adventní víkend. Zdroj: "+SRC_K),
 e("kult-12-stedry-den",12,"2027-12-24","Štědrovečerní procházka","tradice","venku",False,P,"Zdroj: "+SRC_K),
 e("gastro-12-silvestr",12,"2027-12-31","Silvestrovský bál","gastro","uvnitr",False,P,"Zdroj: "+SRC_G),
]

sektory = [
 {"nazev":"Premium","cena":890,"mist":268},
 {"nazev":"Standard","cena":690,"mist":350},
 {"nazev":"Zvyhodnene","cena":490,"mist":200},
 {"nazev":"Promo","cena":590,"mist":50},
 {"nazev":"Sponzorske","cena":0,"mist":34},
]
assert sum(s["mist"] for s in sektory)==902

data = {
 "verze":"1.0",
 "aktualizovano": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
 "zdroj_pravdy":"Zamecka_Resonance_MASTER_MODEL_2027_CFO_FINAL_v2.xlsx",
 "zdroje_poznamka":"CFO FINAL v2 nebyl při sestavení nalezen na disku Macu, v Google Drive ani v Gmailu; hodnoty venue/cenik/ekonomika jsou převzaty ze zadání bloku PROGRAM (2026-09-16), které z CFO v2 vychází. Kalendář: tab kultura index_master.html + ~/Downloads/zamecka-resonance-citoliby.html. Katalog: Divadlo Metro, ověřená data září 2026. Zamek_Citoliby_Gastro_Model_2027_RED.xlsx nebyl čten (bez pythonu).",
 "venue":{
   "nadvori":{"rozmery_m":[25,50],"parter_mist":902},
   "loze":{"ctyrmistne_ks":8,"dvoumistne_ks":4,"kapacita_osob":40,"poznamka":"navic k parteru, arkady v patre, zamereni CHYBI"},
   "zahrada":{"kapacita_koncert":3000,"strop":4300},
   "parkovani_mist":250
 },
 "cenik":{
   "sektory":sektory,
   "loze_cena_os":1990,
   "loze_obsah":"vstup, welcome frizzante, raut 320 Kc, obsluha, prioritni vstup",
   "prirazky":{"premiovy_vecer":0.15,"koncert":0.30,"gala_loze":2500},
   "parkovne":50,
   "dph_vstupne":0.12,
   "dph_zajezd":0.21,
   "benchmark_divice":{"mist":818,"prumer_vstupenka":865,"vyprodano_gross":707882}
 },
 "ekonomika":{
   "break_even_obsazenost":0.388,
   "break_even_hostu":350,
   "honorar_fix_model":140000,
   "doprava_model":8000,
   "pracovni_kapital":518500,
   "doprava_kc_km_vozidlo":16,
   "cekacka_kc_h_vozidlo":300,
   "scenare_ebitda":{"A_krizovy":3568385,"B_konzervativni":4593446,"C_realisticky":6643568,"D_vyprodano":8578333,"E_stretch":10096644}
 },
 "katalog":katalog,
 "kalendar":kal
}
ids=[x["id"] for x in kal]; assert len(ids)==len(set(ids)), "dup ids"
json.dump(data, open("program.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("katalog:",len(katalog),"kalendar:",len(kal))
from collections import Counter
print(Counter(x["typ"] for x in kal)); print("tentpole:",sum(x["tentpole"] for x in kal))
print("bytes:", len(open("program.json","rb").read()))
