# Castello Vendor Matrix

Interní NEXUS modul pro evidence-based výběr ticketingu, distribuce, CRM a performance partnerů Zámku Cítoliby.

## Princip
- Nemíchá core ticketing s externím distribučním boosterem.
- Každé skóre má viditelný zdroj, datum a confidence.
- Neznámé položky zůstávají explicitně neznámé.
- Ekonomika se přepočítává na scénář vstupenky × průměrná ticket price.
- Výsledný score není náhrada smluvního/technického due diligence.

## URL
- UI: `/castello/vendors`
- JSON: `/castello/vendors/api`

## Další iterace
1. DB tabulky vendor / quote / criterion / evidence / scenario / decision.
2. M365 importer pro odpovědi a přílohy.
3. Historie nabídek a změn.
4. TCO model: gateway, surcharge, settlement, chargeback, staff, marketing.
5. Side-by-side contract clauses a risk register.
6. Napojení na Cítoliby program/seating modul.
