"""Seed Axigon account data — LOGPACK, registration, contacts, intake sources."""
from backend.core.models.base import SessionLocal
from backend.core.models.kernel import Entity
from .models import ExternalAccount, ExternalContact, ExternalContactAssignment, IntakeSource


def seed_axigon(db):
    # Find LOGPACK entity
    logpack = db.query(Entity).filter(
        Entity.code.in_(["LOG", "LOGPACK", "SOL"])
    ).first()
    entity_id = logpack.id if logpack else None

    # Skip if already seeded
    existing = db.query(ExternalAccount).filter(
        ExternalAccount.provider_code == "axigon"
    ).first()
    if existing:
        print("Axigon account already seeded.")
        return

    # Create account
    acc = ExternalAccount(
        entity_id=entity_id,
        provider_code="axigon",
        status="active",
        registration_type="Premium",
        registration_valid_to="2027-03-01",
        deposit_amount=70000.00,
        registered_address="Maroldova 1623, 440 01 Louny",
        delivery_address="Chlumčany 165, 439 03 Chlumčany",
        notes=(
            "Důležité: změna emailu NEMĚNÍ přihlašovací jméno. "
            "Přihlašovací jméno a heslo jsou oddělené od kontaktního emailu. "
            "Pokud je nutná změna jména, starý kontakt musí být smazán a vytvořen nový."
        ),
    )
    db.add(acc); db.flush()

    # Contact 1 — Hana Prošková
    c1 = ExternalContact(
        external_account_id=acc.id,
        contact_type="person",
        display_name="Hana Prošková",
        email="hana.proskova@logpack.cz",
        phone="606472366",
        mobile_app_access=True,
        send_invoices=True,
        send_price_lists=True,
        is_active=True,
    )
    db.add(c1); db.flush()

    # Assignments for Hana
    for area in ["contracts", "fuel_cards", "billing"]:
        db.add(ExternalContactAssignment(
            external_contact_id=c1.id,
            area=area, priority="primary", is_primary=True
        ))

    # Contact 2 — faktury@logpack.cz (department/group)
    c2 = ExternalContact(
        external_account_id=acc.id,
        contact_type="department",
        display_name="faktury@logpack.cz",
        email="faktury@logpack.cz",
        phone="606472366",
        mobile_app_access=False,
        send_invoices=True,
        send_price_lists=False,
        is_active=True,
        notes="Skupinový email pro fakturaci. Sekundární billing kontakt.",
    )
    db.add(c2); db.flush()
    db.add(ExternalContactAssignment(
        external_contact_id=c2.id,
        area="billing", priority="secondary", is_primary=False
    ))

    db.commit()
    print(f"Axigon account seeded (entity={entity_id})")

    # Intake sources
    sources = [
        IntakeSource(
            code="mailbox_faktury_logpack",
            source_type="mailbox",
            display_name="faktury@logpack.cz (mailbox)",
            status="active",
            entity_id=entity_id,
            default_for_type="fuel_invoice",
            notes="Axigon PHM faktury přicházejí z tohoto emailu.",
        ),
        IntakeSource(
            code="wflow",
            source_type="workflow",
            display_name="wflow.cz",
            status="active",
            entity_id=entity_id,
            default_for_type="phm",
            notes="wflow.cz — zdrojový systém pro PHM/Axigon dokumenty.",
        ),
        IntakeSource(
            code="manual",
            source_type="manual",
            display_name="Ruční zadání",
            status="active",
            entity_id=None,
            default_for_type="generic",
        ),
    ]
    for s in sources:
        if not db.query(IntakeSource).filter(IntakeSource.code == s.code).first():
            db.add(s)
    db.commit()
    print("Intake sources seeded.")


if __name__ == "__main__":
    db = SessionLocal()
    seed_axigon(db)
    db.close()
