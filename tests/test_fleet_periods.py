"""Synthetic SQLite tests of shared PHM attribution; no production DB access."""
import os
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['SECRET_KEY'] = 'synthetic-fleet-tests-never-use-in-production'
import unittest
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from backend.core.models.base import Base
from backend.core.models.kernel import Person, Entity
from backend.modules.fleet.models import Vehicle, VehicleAssignment, FuelTransaction
from backend.modules.fleet.periods import approved_attributions, driver_phm, decimal_total, strict_date
from backend.modules.fleet.phm_routes import _vehicle_data, _person_data, _months, templates


class FleetPeriodTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        @event.listens_for(self.engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.db.add_all([Person(id='a', first_name='Test', last_name='A'),
                         Person(id='b', first_name='Test', last_name='B'),
                         Entity(id='e', code='TEST', name='Test', legal_name='Test', division='clinic')])
        self.db.flush()
        self.db.add_all([Vehicle(id='v', spz='TEST-01', make='Test', model='Auto', entity_id='e'),
                         Vehicle(id='unknown-entity', spz='TEST-02', make='Test', model='Other')])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def assignment(self, who='a', start='2026-01-01', end=None, vehicle='v'):
        row = VehicleAssignment(id=str(uuid4()), vehicle_id=vehicle, person_id=who, date_from=start, date_to=end)
        self.db.add(row)
        self.db.commit()
        return row

    def transaction(self, day='2026-03-10', year=2026, month=3, driver=None, amount='12.34', status='approved', vehicle='v'):
        row = FuelTransaction(id=str(uuid4()), vehicle_id=vehicle, driver_person_id=driver,
                              transaction_date=day, year=year, month=month,
                              amount_total=Decimal(amount) if amount is not None else None,
                              liters_total=Decimal('1.234'), status=status, source_doc_ref='SYNTHETIC')
        self.db.add(row)
        self.db.commit()
        self.db.expire_all()
        return row

    def records(self):
        return approved_attributions(self.db)

    def test_shared_handover_day_is_unresolved_not_assigned_to_next_driver(self):
        self.assignment(end='2026-03-15')
        self.assignment('b', '2026-03-15')
        before = self.transaction('2026-03-14')
        boundary = self.transaction('2026-03-15')
        after = self.transaction('2026-03-16')
        records = {r.transaction.id: r for r in self.records()}
        self.assertEqual(records[before.id].person_id, 'a')
        self.assertIsNone(records[boundary.id].person_id)
        self.assertIn('Překryv', records[boundary.id].reason)
        self.assertEqual(records[after.id].person_id, 'b')

    def test_monthly_summary_needs_one_assignment_covering_entire_month(self):
        self.assignment()
        self.transaction(None)
        self.assertEqual(self.records()[0].person_id, 'a')

    def test_monthly_summary_not_split_proportionally_after_midmonth_change(self):
        self.assignment(end='2026-03-14')
        self.assignment('b', '2026-03-15')
        self.transaction(None)
        self.assertIsNone(self.records()[0].person_id)

    def test_monthly_whole_month_holder_does_not_override_any_competing_overlap(self):
        self.assignment()
        self.assignment('b', '2026-03-10', '2026-03-11')
        self.transaction(None)
        self.assertIsNone(self.records()[0].person_id)

    def test_monthly_summary_partial_coverage_and_duplicate_assignment_unresolved(self):
        self.assignment(start='2026-03-02')
        self.transaction(None)
        self.assertIsNotNone(self.records()[0].reason)
        self.assignment(start='2026-01-01')
        self.assertIsNotNone(self.records()[0].reason)

    def test_explicit_driver_conflict_does_not_override_history(self):
        self.assignment()
        self.transaction(driver='b')
        r = self.records()[0]
        self.assertIsNone(r.person_id)
        self.assertIn('nesouhlasí', r.reason)
        own, unresolved = driver_phm(self.db, 'b', [])
        self.assertEqual(len(own), 0)
        self.assertEqual(len(unresolved), 1)

    def test_invalid_dates_and_mismatched_period_stay_visible(self):
        self.assignment()
        for day, year, month in [('2026-02-30', 2026, 2), ('2026-3-10', 2026, 3),
                                 ('2026-03-10', 2026, 2), ('', 2026, 3),
                                 (None, 2026, 13), (None, 0, 3), (None, None, 3)]:
            self.transaction(day, year, month)
        records = self.records()
        self.assertEqual(len(records), 7)
        self.assertTrue(all(r.reason for r in records))
        self.assertEqual(sum(m['txn'] for m in _months(records)), 7)
        self.assertTrue(all(m['label'] == 'Neplatné / neznámé období' for m in _months(records)))

    def test_strict_date_rejects_basic_iso_week_dates_and_datetime(self):
        for value in ['20260310', '2026-W11-2', '2026-03-10T12:00:00', ' 2026-03-10', None]:
            with self.assertRaises(ValueError):
                strict_date(value)

    def test_invalid_assignment_cannot_be_silently_ignored(self):
        self.assignment()
        self.assignment('b', 'unknown', None)
        self.transaction()
        self.assertIn('Neplatná historie', self.records()[0].reason)

    def test_future_assignment_does_not_claim_earlier_fuel(self):
        self.assignment(start='2026-04-01')
        self.transaction()
        self.assertIsNone(self.records()[0].person_id)

    def test_reversed_assignment_is_unresolved(self):
        self.assignment(start='2026-03-20', end='2026-03-01')
        self.transaction()
        self.assertIsNotNone(self.records()[0].reason)

    def test_daily_date_without_redundant_month_is_valid(self):
        self.assignment()
        self.transaction(year=None, month=None)
        self.assertEqual(self.records()[0].person_id, 'a')
        self.assertEqual(_months(self.records())[0]['label'], '03/2026')

    def test_both_views_conserve_approved_costs_including_unresolved_and_unknown_entity(self):
        self.assignment(end='2026-03-14')
        self.assignment('b', '2026-03-15')
        self.transaction('2026-03-10', amount='0.10')
        self.transaction(None, amount='0.20')
        self.transaction('2026-03-20', amount='0.30')
        self.transaction(vehicle='unknown-entity', amount='0.40')
        self.transaction(amount='1000', status='draft')
        vehicles, people = _vehicle_data(self.db), _person_data(self.db)
        for view in (vehicles, people):
            self.assertEqual(sum(r['txn'] for r in view), 4)
            self.assertEqual(sum(r['kc'] for r in view), Decimal('1.00'))
        unknown = next(p for p in people if p['person_id'] is None)
        self.assertEqual(unknown['kc'], Decimal('0.60'))
        own, unresolved = driver_phm(self.db, 'a', ['v'])
        self.assertEqual(decimal_total(own, 'amount_total'), Decimal('0.10'))
        self.assertEqual(decimal_total([r.transaction for r in unresolved], 'amount_total'), Decimal('0.20'))
        self.assertEqual(sum(v['kc'] for v in _vehicle_data(self.db, 'TEST')), Decimal('0.60'))

    def test_missing_amount_not_reported_as_known_zero(self):
        self.transaction(amount=None)
        row = _vehicle_data(self.db)[0]
        self.assertEqual(row['missing_amount'], 1)
        self.assertIsNone(row['drivers'][0]['months'][0]['transactions'][0]['kc'])

    def test_actual_driver_detail_renders_verified_and_unresolved_separately(self):
        from types import SimpleNamespace
        from fastapi import Request
        from backend.modules.fleet.driver_routes import driver_detail
        self.assignment(end='2026-03-14')
        self.assignment('b', '2026-03-15')
        self.transaction('2026-03-10', amount='10.25')
        self.transaction(None, amount='99.99')
        request = Request({'type': 'http', 'method': 'GET', 'path': '/fleet/driver/a',
                           'headers': [], 'app': SimpleNamespace(state=SimpleNamespace(hr_enabled=False))})
        user = SimpleNamespace(email='test', role='owner', roles=['owner'],
                               person=SimpleNamespace(first_name='Test'), has_role=lambda *x: True)
        response = driver_detail('a', request, self.db, user)
        html = response.body.decode()
        self.assertEqual(response.context['phm_total_kc'], Decimal('10.25'))
        self.assertEqual(response.context['phm_unresolved_kc'], Decimal('99.99'))
        self.assertIn('K ověření', html)
        self.assertIn('SYNTHETIC', html)

    def test_templates_compile_and_unresolved_source_reason_are_rendered(self):
        self.transaction(day='bad')
        for name in ('pages/fleet/phm2.html', 'pages/fleet/driver_detail.html'):
            templates.env.get_template(name)
        # Render the content block in isolation: no auth/base layout assumptions.
        template = templates.env.get_template('pages/fleet/phm2.html')
        from types import SimpleNamespace
        context = template.new_context(dict(data=_vehicle_data(self.db), view='vozidla', entity=None,
                       entities=['TEST'], total_kc=Decimal('12.34'), total_lit=Decimal('1.234'),
                       total_txn=1, missing_amount=0, current_user=SimpleNamespace(email='test')))
        # Macro globals are assigned by root_render_func before block use.
        html = template.render(context.get_all(), request=SimpleNamespace(url=SimpleNamespace(path='/fleet/phm'), app=SimpleNamespace(state=SimpleNamespace(hr_enabled=False))),
                               current_user=SimpleNamespace(email='test', role='owner', roles=['owner'],
                               person=SimpleNamespace(full_name='Test'), has_role=lambda *x: True))
        self.assertIn('Neplatné nebo rozporné', html)
        self.assertIn('SYNTHETIC', html)
        self.assertIn('K ověření', html)


if __name__ == '__main__':
    unittest.main()
