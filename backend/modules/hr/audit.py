from .models import HREvent


def record(db, case_id, kind, actor, **details):
    db.add(HREvent(case_id=case_id, kind=kind, actor_id=actor.id,
                   actor_type='invitation' if getattr(actor, 'portal', False) else 'account',
                   details=details))
