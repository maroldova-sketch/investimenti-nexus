import json
import os
from copy import deepcopy

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "providers.json")

LENSES = {
    "CEO / DTC core": {
        "ownership": 18, "economics": 16, "cashflow": 10, "data": 15,
        "features": 12, "integrations": 8, "distribution": 3, "marketing": 5,
        "addons": 6, "ops": 4, "contract": 3,
    },
    "CFO / TCO": {
        "ownership": 5, "economics": 32, "cashflow": 18, "data": 5,
        "features": 5, "integrations": 3, "distribution": 2, "marketing": 2,
        "addons": 10, "ops": 5, "contract": 13,
    },
    "CTO / data": {
        "ownership": 20, "economics": 5, "cashflow": 3, "data": 25,
        "features": 12, "integrations": 18, "distribution": 2, "marketing": 2,
        "addons": 3, "ops": 5, "contract": 5,
    },
    "CMO / growth": {
        "ownership": 5, "economics": 8, "cashflow": 2, "data": 15,
        "features": 5, "integrations": 8, "distribution": 25, "marketing": 22,
        "addons": 2, "ops": 4, "contract": 4,
    },
    "COO / event ops": {
        "ownership": 5, "economics": 10, "cashflow": 8, "data": 5,
        "features": 22, "integrations": 8, "distribution": 4, "marketing": 3,
        "addons": 8, "ops": 20, "contract": 7,
    },
    "RED TEAM": {
        "ownership": 16, "economics": 12, "cashflow": 14, "data": 10,
        "features": 7, "integrations": 7, "distribution": 4, "marketing": 3,
        "addons": 6, "ops": 7, "contract": 14,
    },
    "Distribution booster": {
        "ownership": 5, "economics": 10, "cashflow": 5, "data": 10,
        "features": 8, "integrations": 7, "distribution": 25, "marketing": 20,
        "addons": 2, "ops": 5, "contract": 3,
    },
}

def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)

def weighted_score(provider, lens):
    scores = provider.get("scores", {})
    weights = LENSES[lens]
    total = 0.0
    used = 0.0
    for key, weight in weights.items():
        value = scores.get(key)
        if value is None:
            continue
        total += float(value) * weight
        used += weight
    return round(total / used, 1) if used else None

def swarm(provider):
    out = {}
    for lens in LENSES:
        out[lens] = weighted_score(provider, lens)
    core = [
        out["CEO / DTC core"], out["CFO / TCO"], out["CTO / data"],
        out["CMO / growth"], out["COO / event ops"], out["RED TEAM"],
    ]
    out["Consensus"] = round(sum(core) / len(core), 1)
    return out

def provider_cost(provider, scenario):
    revenue = float(scenario["ticket_revenue"])
    tickets = int(scenario["tickets"])
    orders = int(scenario["orders"])
    pid = provider["id"]
    result = {
        "organizer_fee": None,
        "customer_surcharge": None,
        "cashflow_note": provider.get("cashflow_note", ""),
        "known_cost_per_ticket": None,
        "note": "",
    }

    if pid == "bzuco":
        fee = revenue * 0.035
        result.update(
            organizer_fee=round(fee),
            customer_surcharge="volitelný; zůstává Castello",
            known_cost_per_ticket=round(fee / max(tickets, 1), 2),
            note="Nezahrnuje vlastní platební bránu. Pevný roční poplatek je otevřená varianta.",
        )
    elif pid == "xticket":
        fee = revenue * 0.04
        result.update(
            organizer_fee=round(fee),
            customer_surcharge="0-4 % dle rozdělení",
            known_cost_per_ticket=round(fee / max(tickets, 1), 2),
            note="Alternativa: 0 Kč pořadateli a 4 % nad cenu hradí kupující; případně split 2/2.",
        )
    elif pid == "smsticket":
        fee = revenue * 0.05
        result.update(
            organizer_fee=round(fee),
            customer_surcharge=round(orders * 10),
            known_cost_per_ticket=round(fee / max(tickets, 1), 2),
            note="Email připouští individuální slevu v řádu desetin procenta. Pokladna 3-5 Kč / ticket.",
        )
    elif pid == "plg":
        result.update(
            organizer_fee=None,
            customer_surcharge="nabídka dosud nedoručena",
            known_cost_per_ticket=None,
            note="Pro DTC core nepočítáme bez konkrétní nabídky. Modul ho vede primárně jako distribuční booster.",
        )
    return result

def build_view(scenario=None):
    data = load_data()
    scenario = scenario or deepcopy(data["default_scenario"])
    providers = []
    for p in data["providers"]:
        item = deepcopy(p)
        item["swarm"] = swarm(item)
        item["cost"] = provider_cost(item, scenario)
        providers.append(item)

    providers.sort(key=lambda x: x["swarm"]["CEO / DTC core"] or 0, reverse=True)
    return {
        **data,
        "scenario": scenario,
        "providers": providers,
        "lenses": list(LENSES.keys()),
    }
