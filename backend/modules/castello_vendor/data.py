from dataclasses import dataclass, asdict
from typing import Optional

CRITERIA = [
    {"key":"ownership","label":"White-label / vlastnictví vztahu","weight":20},
    {"key":"economics","label":"Ekonomika a škálování","weight":20},
    {"key":"attribution","label":"Attribution / first-party data","weight":15},
    {"key":"cashflow","label":"Cash-flow / merchant model","weight":10},
    {"key":"ops","label":"Seating / check-in / refundace","weight":10},
    {"key":"integration","label":"API / integrace / rozšiřitelnost","weight":10},
    {"key":"distribution","label":"Externí distribuce / reach","weight":10},
    {"key":"support","label":"Onboarding / podpora","weight":5},
]

VENDORS = [
    {
        "id":"bzuco","name":"BZUCO","role":"Core ticketing / white-label",
        "status":"active_quote","evidence_date":"2026-09-18","confidence":0.92,
        "fee":{"model":"3.5 % ze všech ticket sales","percent":3.5,"customer_fee":"nastavitelný; celý zůstává pořadateli","fixed_option":"ano, individuální roční paušál","gateway":"vlastní platební brána pořadatele; náklad brány navíc"},
        "scores":{"ownership":5,"economics":4.2,"attribution":5,"cashflow":5,"ops":5,"integration":4.3,"distribution":1.5,"support":4.5},
        "facts":[
            "Checkout pod značkou a doménou pořadatele, vlastní platební brána, vlastní databáze.",
            "Event Intelligence / Prodejní Radar: zdroj → objednávka → vstupenky → tržba.",
            "Ecomail/SmartEmailing sync; offline check-in; seating; refundace; vlny/poukazy.",
            "F&B, parking, merch a hospitality: deklarováno 0 % provize.",
            "Nevýhradnost a nulová minimální kvóta jsou přijatelné.",
            "Nemá marketplace/publikum; performance kampaně nabízí zvlášť."
        ],
        "unknowns":["Konkrétní objemová sazba / fixní roční cena","Cena platební brány","Rozsah a dokumentace API/webhooků","Cena lidské administrace a cashless"],
        "source":"Mail Jiří Blafka, 18. 9. 2026"
    },
    {
        "id":"xticket","name":"xTicket","role":"Portál / hybrid distribuce",
        "status":"active_quote","evidence_date":"2026-09-18","confidence":0.90,
        "fee":{"model":"4 %; lze přenést na kupujícího nebo dělit","percent":4.0,"customer_fee":"0–4 % dle nastavení","fixed_option":"neuvedeno","gateway":"platební brána xTicket"},
        "scores":{"ownership":1.5,"economics":4.1,"attribution":4.0,"cashflow":2.5,"ops":4.7,"integration":2.8,"distribution":4.2,"support":4.5},
        "facts":[
            "Výslovně uvádí, že nefunguje jako white-label; prodejní kanál je xticket.cz.",
            "4 % provize, nebo 4 % transakční poplatek kupujícímu; lze kombinovat.",
            "Dashboard uvádí prodeje, návštěvnost, referrer a geografii; denní e-mail report.",
            "Newslettery/pozvánky a podpora na sociálních sítích uváděna zdarma.",
            "Offline mobilní check-in, seating, promo kódy, vlny, refundace.",
            "Vyplacení nejpozději týden po akci; nový pořadatel může žádat max. 50 % průběžně.",
            "Marketing Meta/Instagram: správa za 10 % reklamního rozpočtu."
        ],
        "unknowns":["API/webhooky","Export úplné zákaznické databáze a souhlasy","Dynamické externí kvóty","Individuální sazba pro 18k+ vstupenek"],
        "source":"Mail Matyáš Havelka + přílohy, 18. 9. 2026"
    },
    {
        "id":"smsticket","name":"smsticket","role":"Portál / robustní ticketing",
        "status":"active_quote","evidence_date":"2026-09-18","confidence":0.91,
        "fee":{"model":"5 % online; možná sleva v desetinách p.b.","percent":5.0,"customer_fee":"10 Kč za celý nákup","fixed_option":"pokladna 3–5 Kč / vstupenka","gateway":"součást jejich infrastruktury"},
        "scores":{"ownership":2.2,"economics":3.2,"attribution":3.7,"cashflow":3.0,"ops":4.8,"integration":3.0,"distribution":3.6,"support":4.3},
        "facts":[
            "Online provize se neliší podle zdroje zákazníka; promo pořadatele vs. promo smsticket nemá odlišnou sazbu.",
            "Vlastní Statistiky: návštěvnost, UTM a zdroje; nákup+zdroj lze kombinovat s GA4.",
            "Tracking je podle nich z principu ztrátový; interní návštěvnická data jsou anonymní.",
            "Fyzická pokladna max. 3–5 Kč / vstupenka.",
            "F&B/alkohol neobsluhují; parking přes Parkum."
        ],
        "unknowns":["Finální individuální procento","Přesná marketingová nabídka / incremental reach","API/webhooky a export kontaktů","Aktuální settlement podmínky v konkrétní nabídce"],
        "source":"Mail Jan Barnet, 16. a 18. 9. 2026"
    },
    {
        "id":"plg","name":"PLG / GoOut / Ticketportal","role":"Distribution booster",
        "status":"awaiting_quote","evidence_date":"2026-09-16","confidence":0.55,
        "fee":{"model":"individuální nabídka zatím nepřišla","percent":None,"customer_fee":"neověřeno pro Cítoliby","fixed_option":"neověřeno","gateway":"portálový model"},
        "scores":{"ownership":1.2,"economics":2.5,"attribution":3.2,"cashflow":2.5,"ops":4.5,"integration":3.5,"distribution":5.0,"support":3.8},
        "facts":["Po e-mailu pouze výzva k registraci pořadatele; konkrétní obchodní nabídka zatím chybí.","Strategická role pro Cítoliby: externí reach / marketplace, ne nutně core DTC infrastruktura."],
        "unknowns":["Cena","Marketingový balík","Kvóty/neexkluzivita","Attribution a data ownership v konkrétní smlouvě"],
        "source":"GoOut mail 16. 9. 2026 + předchozí veřejné benchmarky"
    },
]

COMPANIONS = [
    {"name":"Ecomail","role":"Marketing automation / newsletter / SMS","status":"tech call offered","fit":"vysoký","note":"Dává smysl jako komunikační vrstva nad ticketingovým source-of-truth."},
    {"name":"HUBIO","role":"Performance ticket marketing","status":"nabídka doručena; schůzku odložit","fit":"vysoký později","note":"Silné měření CAC/ROAS a creative; řešit po volbě ticketingu a cen."},
]

def weighted_score(vendor):
    score = 0.0
    for c in CRITERIA:
        score += (vendor["scores"].get(c["key"],0) / 5.0) * c["weight"]
    return round(score,1)

def scenario_cost(vendor, ticket_count: int, avg_ticket: float):
    pct = vendor["fee"].get("percent")
    turnover = ticket_count * avg_ticket
    return None if pct is None else round(turnover * pct / 100.0)

def payload(ticket_count: int = 18000, avg_ticket: float = 1200):
    rows=[]
    for v in VENDORS:
        item=dict(v)
        item["score"]=weighted_score(v)
        item["scenario_cost"]=scenario_cost(v,ticket_count,avg_ticket)
        rows.append(item)
    return {
        "criteria":CRITERIA,
        "vendors":sorted(rows,key=lambda x:x["score"],reverse=True),
        "companions":COMPANIONS,
        "scenario":{"tickets":ticket_count,"avg_ticket":avg_ticket,"turnover":ticket_count*avg_ticket},
        "updated_at":"2026-09-20",
        "method":"0–5 score × explicit weight; unknowns remain visible; confidence is evidence completeness, not vendor quality."
    }
