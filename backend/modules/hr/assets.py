"""HR pages reference their script and stylesheet by content version.

The page itself is never stored, but `/static/hr/app.js` may be kept for hours by
a browser or the public proxy whatever the origin says (the tunnel's CDN replaces
`no-cache` with its own browser lifetime). A release would then run the previous
script against the new API. An address that changes with the file content makes
every release visible on the next page load, without purging any cache.
"""
import hashlib
from pathlib import Path
from fastapi.responses import HTMLResponse

STATIC = Path(__file__).resolve().parents[3] / 'frontend/static/hr'
ASSETS = ('app.js', 'style.css')
_versions = {}


def asset_version(name):
    path = STATIC / name
    stat = path.stat()
    stamp = (stat.st_mtime_ns, stat.st_size)
    cached = _versions.get(name)
    if cached is None or cached[0] != stamp:
        cached = _versions[name] = (stamp, hashlib.sha256(path.read_bytes()).hexdigest()[:16])
    return cached[1]


def page(name, headers=None):
    html = (STATIC / name).read_text(encoding='utf-8')
    for asset in ASSETS:
        reference = f'"/static/hr/{asset}"'
        if reference not in html:
            raise RuntimeError(f'{name} does not reference {asset}; review the release.')
        html = html.replace(reference, f'"/static/hr/{asset}?v={asset_version(asset)}"')
    return HTMLResponse(html, headers=headers)
