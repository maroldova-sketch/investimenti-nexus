"""NEXUS → Elias dispatcher bridge.

Safe wrapper kolem `~/andrew/elias/nexus_dispatcher.py`.
Všechna volání jsou NEBLOKUJÍCÍ pro NEXUS request flow:
  - exception v dispatcheru → log WARN, nikdy nezabije request
  - fire-and-forget přes thread pro gov/approval (Teams/Planner volání trvají ~1-2s)

Use:
    from backend.core.dispatcher import (
        dispatch_gov_message_safe,
        dispatch_approval_case_safe,
        dispatch_fuel_anomaly_safe,
    )

    dispatch_gov_message_safe(schranka_name=..., subject=..., ...)
"""
import logging
import sys
import threading
from pathlib import Path
from typing import Optional

log = logging.getLogger("nexus.dispatcher")

# Inject Elias runtime path
ELIAS_PATH = str(Path.home() / "andrew" / "elias")
if ELIAS_PATH not in sys.path:
    sys.path.insert(0, ELIAS_PATH)


def _dispatch_async(fn_name: str, **kwargs):
    """Fire-and-forget dispatcher call v thread, žádný návratový hodnota."""
    def _run():
        try:
            import nexus_dispatcher as ND
            fn = getattr(ND, fn_name)
            result = fn(**kwargs)
            log.info(f"dispatcher {fn_name} OK: teams={result.get('teams',{}).get('ok')} planner={result.get('planner',{}).get('ok')}")
        except Exception as e:
            log.warning(f"dispatcher {fn_name} FAIL: {e}")
    
    t = threading.Thread(target=_run, name=f"disp-{fn_name}", daemon=True)
    t.start()


def dispatch_gov_message_safe(
    schranka_name: str,
    subject: str,
    sender: str,
    received_at: str,
    is_urgent: bool = False,
    deadline: Optional[str] = None,
    nexus_ref: Optional[str] = None,
    nexus_link: Optional[str] = None,
):
    """📬 ISDS zpráva → Teams + Planner. Neblokující."""
    _dispatch_async(
        "dispatch_gov_message",
        schranka_name=schranka_name,
        subject=subject,
        sender=sender,
        received_at=received_at,
        is_urgent=is_urgent,
        deadline=deadline,
        nexus_ref=nexus_ref,
        nexus_link=nexus_link,
    )


def dispatch_approval_case_safe(
    case_type: str,
    title: str,
    amount: Optional[float] = None,
    person_name: Optional[str] = None,
    description: Optional[str] = None,
    nexus_link: Optional[str] = None,
):
    """💳 Approval → Teams + Planner. Neblokující."""
    _dispatch_async(
        "dispatch_approval_case",
        case_type=case_type,
        title=title,
        amount=amount,
        person_name=person_name,
        description=description,
        nexus_link=nexus_link,
    )


def dispatch_fuel_anomaly_safe(vehicle: str, spz: str, amount: float, reason: str):
    """⛽ PHM anomálie → Teams + Planner. Neblokující."""
    _dispatch_async(
        "dispatch_fuel_anomaly",
        vehicle=vehicle,
        spz=spz,
        amount=amount,
        reason=reason,
    )
