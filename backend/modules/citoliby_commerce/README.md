# Cítoliby Commerce Intelligence

Interní rozhodovací modul NEXUS pro výběr a řízení ticketingu, CRM, distribuce a performance partnerů Zámku Cítoliby.

## Princip
- fakta oddělená od tvrzení dodavatelů a odhadů,
- každý údaj má zdroj / datum / confidence,
- náklady se počítají ze scénáře, nikoli z pocitu,
- scoring má více nezávislých pohledů (CEO, CFO, CTO, CMO, COO, RED TEAM),
- DTC core a distribuční booster se posuzují odděleně.

## Route
- /citoliby/commerce
- /citoliby/commerce/api/summary

## Další vývoj
1. ingest relevantních mailů z M365,
2. evidence registry smluv,
3. ukládání nabídek a smluv do DB,
4. verzování scoringu a vah,
5. scénáře pro akce / sezony,
6. reálná prodejní data po výběru platformy,
7. napojení Ecomail / performance / ticketing webhooků.
