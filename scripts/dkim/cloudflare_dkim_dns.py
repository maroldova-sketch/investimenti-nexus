"""Add/update DKIM selector1+selector2 CNAME records in Cloudflare DNS.

Required env:
  CF_API_TOKEN   Cloudflare API token with Zone.DNS:Edit on the target zones.
  ONMICROSOFT    Tenant onmicrosoft.com host (e.g. "vasezubnicentrum.onmicrosoft.com").

Usage:
  python cloudflare_dkim_dns.py                    # all 4 domains
  python cloudflare_dkim_dns.py investimenti.cz    # one domain
"""
from __future__ import annotations

import os
import sys
from typing import Iterable

import httpx

API = "https://api.cloudflare.com/client/v4"

DEFAULT_DOMAINS = [
    "investimenti.cz",
    "vzc.cz",
    "logpack.cz",
    "zamek-citoliby.cz",
]


def selector_target(domain: str, selector: str, onmicrosoft: str) -> str:
    slug = domain.replace(".", "-")
    return f"{selector}-{slug}._domainkey.{onmicrosoft}"


def get_zone_id(client: httpx.Client, domain: str) -> str:
    r = client.get(f"{API}/zones", params={"name": domain})
    r.raise_for_status()
    result = r.json()["result"]
    if not result:
        raise SystemExit(f"Zone not found in Cloudflare: {domain}")
    return result[0]["id"]


def find_record(client: httpx.Client, zone_id: str, name: str) -> dict | None:
    r = client.get(f"{API}/zones/{zone_id}/dns_records", params={"name": name, "type": "CNAME"})
    r.raise_for_status()
    items = r.json()["result"]
    return items[0] if items else None


def upsert_cname(client: httpx.Client, zone_id: str, name: str, target: str) -> str:
    payload = {"type": "CNAME", "name": name, "content": target, "ttl": 1, "proxied": False}
    existing = find_record(client, zone_id, name)
    if existing:
        if existing["content"] == target:
            return "unchanged"
        r = client.put(f"{API}/zones/{zone_id}/dns_records/{existing['id']}", json=payload)
        r.raise_for_status()
        return "updated"
    r = client.post(f"{API}/zones/{zone_id}/dns_records", json=payload)
    r.raise_for_status()
    return "created"


def run(domains: Iterable[str]) -> None:
    token = os.environ.get("CF_API_TOKEN")
    onmicrosoft = os.environ.get("ONMICROSOFT")
    if not token:
        raise SystemExit("CF_API_TOKEN not set")
    if not onmicrosoft:
        raise SystemExit("ONMICROSOFT not set (e.g. 'vasezubnicentrum.onmicrosoft.com')")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(headers=headers, timeout=30.0) as client:
        for domain in domains:
            print(f"\n=== {domain} ===")
            zone_id = get_zone_id(client, domain)
            for selector in ("selector1", "selector2"):
                name = f"{selector}._domainkey.{domain}"
                target = selector_target(domain, selector, onmicrosoft)
                action = upsert_cname(client, zone_id, name, target)
                print(f"  {name}  ->  {target}  [{action}]")


if __name__ == "__main__":
    args = sys.argv[1:]
    run(args if args else DEFAULT_DOMAINS)
