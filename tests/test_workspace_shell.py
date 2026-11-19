"""Shared navigation and provider-boundary regressions; no live DB/provider writes."""
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.routing import Match

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.anchors = 0
        self.nested = False

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.nested |= self.anchors > 0
            self.anchors += 1
            self.links.append(dict(attrs))

    def handle_endtag(self, tag):
        if tag == 'a':
            self.anchors = max(0, self.anchors - 1)


class WorkspaceShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = Environment(loader=FileSystemLoader(ROOT / 'frontend/templates'), autoescape=select_autoescape())
        cls.groups = cls.env.get_template('layouts/workspace.html').module.groups
        import main
        cls.app = main.app

    def render(self, path, hr=True, fleet=True):
        request = NS(url=NS(path=path), app=NS(state=NS(hr_enabled=hr, fleet_pilot_enabled=fleet)))
        return self.env.get_template('layouts/base.html').render(request=request, current_user=None)

    def first_route(self, path):
        scope = {'type':'http', 'method':'GET', 'path':path, 'root_path':''}
        return next(route for route in self.app.routes if route.matches(scope)[0] == Match.FULL)

    def test_all_templates_compile(self):
        for name in self.env.list_templates():
            with self.subTest(name=name):
                self.env.get_template(name)

    def test_every_menu_link_resolves_to_its_literal_read_page(self):
        for group in self.groups:
            for item in group['links']:
                if item['key'] in ('hr', 'fleet-operations'):
                    continue  # Feature routes are conditionally installed, as are their menu items.
                with self.subTest(path=item['href']):
                    self.assertEqual(item['href'], self.first_route(item['href']).path)

    def test_specific_fleet_and_mail_pages_not_shadowed_by_ids(self):
        for path, handler in [('/fleet/trips','trip_list'),('/fleet/phm','phm_overview'),
                              ('/m365/mail/search','mail_search'),('/m365/mail/compose','mail_compose')]:
            with self.subTest(path=path):
                self.assertEqual(handler, self.first_route(path).name)

    def test_distinct_section_and_one_active_link_for_every_landing(self):
        for group in self.groups:
            for item in group['links']:
                with self.subTest(path=item['href']):
                    html = self.render(item['href'])
                    self.assertIn(f'data-workspace="{group["key"]}"', html)
                    parser = Links(); parser.feed(html)
                    active = [link for link in parser.links if link.get('aria-current') == 'page']
                    self.assertEqual([item['href']], [link['href'] for link in active])
                    self.assertFalse(parser.nested)
                    menu = [link['href'] for link in parser.links if 'nav-link' in link.get('class','').split()]
                    self.assertEqual(len(menu), len(set(menu)))

    def test_nested_page_uses_most_specific_guide(self):
        self.assertIn('data-workspace="finance"', self.render('/fleet/deductions/123'))
        self.assertIn('data-workspace="people"', self.render('/people/hr'))

    def test_disabled_hr_is_not_advertised(self):
        self.assertNotIn('href="/people/hr"', self.render('/people', hr=False))

    def test_disabled_fleet_pilot_is_not_advertised(self):
        self.assertNotIn('href="/fleet/operations"', self.render('/fleet', fleet=False))
        self.assertIn('href="/fleet/operations"', self.render('/fleet', fleet=True))


class MicrosoftReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main
        from backend.core.security.auth import get_current_user
        cls.app = main.app
        cls.user_dependency = get_current_user

    def setUp(self):
        self.app.dependency_overrides[type(self).user_dependency] = lambda: NS(email='qa@example.invalid', person=NS(first_name='QA'))
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()

    def test_compose_page_does_not_request_message_id(self):
        with patch('backend.modules.m365.routes.m365.get_message') as fetch:
            response = self.client.get('/m365/mail/compose')
        self.assertEqual(200, response.status_code)
        self.assertIn('action="/m365/mail/send"', response.text)
        fetch.assert_not_called()

    def test_search_calls_search_without_reading_fake_message(self):
        with patch('backend.modules.m365.routes.m365.search_messages', return_value={'value':[]}) as search, \
             patch('backend.modules.m365.routes.m365.get_message') as fetch:
            response = self.client.get('/m365/mail/search?q=projekt')
        self.assertEqual(200, response.status_code)
        search.assert_called_once_with('projekt')
        fetch.assert_not_called()

    def test_token_error_is_actionable_without_leaking_provider_details(self):
        with patch('backend.modules.m365.routes.m365.list_messages', side_effect=RuntimeError('secret-token-and-provider-body')):
            response = self.client.get('/m365/mail')
        self.assertEqual(503, response.status_code)
        self.assertIn('Připojení Microsoft 365 potřebuje kontrolu', response.text)
        self.assertNotIn('secret-token', response.text)
        self.assertEqual('private, no-store', response.headers['cache-control'])

    def test_rate_limit_preserves_retry_after_without_automatic_retry(self):
        provider_response = httpx.Response(429, headers={'Retry-After':'45'}, request=httpx.Request('GET','https://graph.microsoft.com/v1.0/me'))
        error = httpx.HTTPStatusError('private diagnostic', request=provider_response.request, response=provider_response)
        with patch('backend.modules.m365.routes.m365.list_contacts', side_effect=error) as load:
            response = self.client.get('/m365/contacts')
        self.assertEqual(429, response.status_code)
        self.assertEqual('45', response.headers['retry-after'])
        self.assertIn('za 45 sekund', response.text)
        self.assertNotIn('private diagnostic', response.text)
        load.assert_called_once()

    def test_provider_permission_failure_not_reported_as_empty_success(self):
        provider_response = httpx.Response(403, request=httpx.Request('GET','https://graph.microsoft.com/v1.0/me'))
        error = httpx.HTTPStatusError('private diagnostic', request=provider_response.request, response=provider_response)
        with patch('backend.modules.m365.routes.m365.list_drive_root', side_effect=error):
            response = self.client.get('/m365/files')
        self.assertEqual(403, response.status_code)
        self.assertIn('Data nejsou načtená', response.text)
        self.assertNotIn('private diagnostic', response.text)

    def test_long_provider_backoff_is_not_shortened(self):
        from backend.modules.m365.routes import _retry_seconds
        self.assertEqual(3600, _retry_seconds('3600'))


if __name__ == '__main__':
    unittest.main()
