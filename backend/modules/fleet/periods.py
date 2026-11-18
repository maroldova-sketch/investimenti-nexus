"""Conservative attribution of legacy fuel records; no writes or inferred handovers.

Legacy assignments contain dates, not instants. Their end date is treated as
inclusive for candidate detection: a shared handover day is ambiguous, never
silently assigned to the next driver. A monthly aggregate requires one assignment
covering the whole month with no other overlapping assignment (even the same
person). Explicit driver IDs are evidence to reconcile, not an override.
"""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re

from .models import FuelTransaction, VehicleAssignment


def strict_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Datum musí být YYYY-MM-DD")
    return date.fromisoformat(value)


def transaction_period(transaction):
    """Return inclusive start/end or raise; never silently normalize bad dates."""
    year, month = transaction.year, transaction.month
    if year is not None and (type(year) is not int or not 1 <= year <= 9999):
        raise ValueError("Neplatný rok")
    if month is not None and (type(month) is not int or not 1 <= month <= 12):
        raise ValueError("Neplatný měsíc")
    if transaction.transaction_date is not None:
        day = strict_date(transaction.transaction_date)
        if (year is not None and day.year != year) or (month is not None and day.month != month):
            raise ValueError("Datum nesouhlasí s obdobím")
        return day, day
    if year is None or month is None:
        raise ValueError("Chybí datum nebo měsíc a rok")
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


@dataclass(frozen=True)
class Attribution:
    transaction: FuelTransaction
    person_id: str | None
    assignment_id: str | None
    reason: str | None


def attribute_transaction(transaction, assignments):
    def unresolved(reason):
        return Attribution(transaction, None, None, reason)

    try:
        first, last = transaction_period(transaction)
    except (ValueError, TypeError):
        return unresolved("Neplatné nebo rozporné datum/období transakce")
    candidates = []
    for assignment in assignments:
        if assignment.vehicle_id != transaction.vehicle_id:
            continue
        try:
            start = strict_date(assignment.date_from)
            end = strict_date(assignment.date_to) if assignment.date_to is not None else date.max
            if end < start or not assignment.person_id:
                raise ValueError("Neplatné svěření")
        except (ValueError, TypeError):
            # Cannot prove that a malformed interval is outside this period.
            return unresolved("Neplatná historie svěření vozidla")
        if start <= last and end >= first:
            candidates.append((assignment, start, end))
    if not candidates:
        return unresolved("Pro období není doloženo svěření")
    if len(candidates) != 1:
        return unresolved("Překryv svěření nebo změna řidiče v období; nutný přesnější podklad")
    assignment, start, end = candidates[0]
    if start > first or end < last:
        return unresolved("Svěření nepokrývá celé období souhrnu")
    if transaction.driver_person_id is not None and transaction.driver_person_id != assignment.person_id:
        return unresolved("Řidič v transakci nesouhlasí s historií svěření")
    return Attribution(transaction, assignment.person_id, assignment.id, None)


def approved_attributions(db, vehicle_ids=None):
    query = db.query(FuelTransaction).filter(FuelTransaction.status == "approved")
    if vehicle_ids is not None:
        query = query.filter(FuelTransaction.vehicle_id.in_(vehicle_ids))
    transactions = query.order_by(FuelTransaction.year, FuelTransaction.month,
                                  FuelTransaction.transaction_date, FuelTransaction.id).all()
    ids = {t.vehicle_id for t in transactions}
    assignments = db.query(VehicleAssignment).filter(VehicleAssignment.vehicle_id.in_(ids)).all() if ids else []
    by_vehicle = {}
    for assignment in assignments:
        by_vehicle.setdefault(assignment.vehicle_id, []).append(assignment)
    return [attribute_transaction(t, by_vehicle.get(t.vehicle_id, [])) for t in transactions]


def decimal_total(transactions, field):
    """Sum the persisted precision; missing values are not asserted to be zero."""
    return sum((Decimal(str(getattr(t, field))) for t in transactions
                if getattr(t, field) is not None), Decimal("0"))


def driver_phm(db, person_id, vehicle_ids):
    # Include explicit references too, so a conflicting imported driver is visible.
    records = approved_attributions(db)
    assigned = [r.transaction for r in records if r.person_id == person_id]
    unresolved = [r for r in records if r.reason and
                  (r.transaction.vehicle_id in vehicle_ids or r.transaction.driver_person_id == person_id)]
    return assigned, unresolved
