"""Outermost gate of the public employee service (behind the local TLS tunnel).

Bounds request size, concurrency and per-client rates before any route runs.
The client address comes from Cloudflare's CF-Connecting-IP only; the service
listens on loopback, so only the local tunnel connector can set it.
"""
import time
from collections import defaultdict, deque
from starlette.responses import JSONResponse

UPLOAD_LIMIT = 8 * 1024 * 1024 + 64 * 1024
BODY_LIMIT = 128 * 1024
RULES = [  # (path predicate, max requests, window seconds)
    (lambda p: p == '/hr/api/open', 20, 600),
    (lambda p: p == '/hr/api/code', 6, 600),
    (lambda p: p == '/hr/api/verify', 20, 600),
    (lambda p: p.startswith('/hr/api/'), 600, 600),
    (lambda p: True, 900, 600),
]


class EntryGuard:
    def __init__(self, app, max_active=32, max_uploads=4, clock=time.monotonic):
        self.app, self.max_active, self.max_uploads, self.clock = app, max_active, max_uploads, clock
        self.active = self.uploads = 0
        self.hits = defaultdict(deque)

    def client(self, scope):
        for name, raw in scope.get('headers', []):
            if name == b'cf-connecting-ip':
                return raw.decode('latin-1')[:64]
        return (scope.get('client') or ('unknown',))[0]

    def limited(self, client, path):
        now = self.clock()
        if len(self.hits) > 20000:
            self.hits = defaultdict(deque, {k: v for k, v in self.hits.items() if v and v[-1] > now - 600})
        for index, (applies, limit, window) in enumerate(RULES):
            if not applies(path):
                continue
            bucket = self.hits[(client, index)]
            while bucket and bucket[0] <= now - window:
                bucket.popleft()
            if len(bucket) >= limit:
                return True
            bucket.append(now)
        return False

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        path, method = scope.get('path', ''), scope.get('method', '')
        headers = dict(scope.get('headers', []))

        async def deny(status, detail):
            await JSONResponse({'detail': detail}, status_code=status,
                               headers={'Cache-Control': 'no-store'})(scope, receive, send)
        if method not in {'GET', 'HEAD', 'POST', 'PUT'}:
            return await deny(405, 'Metoda není povolena.')
        upload = method == 'POST' and path.startswith('/hr/api/cases/') and path.endswith('/documents')
        if method in {'POST', 'PUT'}:
            raw = headers.get(b'content-length')
            if raw is None or not raw.isdigit():
                return await deny(411, 'Požadavek musí uvést svou délku.')
            if int(raw) > (UPLOAD_LIMIT if upload else BODY_LIMIT):
                return await deny(413, 'Požadavek je příliš velký.')
        if self.limited(self.client(scope), path):
            return await deny(429, 'Příliš mnoho pokusů. Zkuste to prosím za několik minut.')
        if self.active >= self.max_active or (upload and self.uploads >= self.max_uploads):
            return await deny(503, 'Služba je právě vytížená. Zkuste to prosím za chvíli.')
        self.active += 1
        self.uploads += upload
        try:
            await self.app(scope, receive, send)
        finally:
            self.active -= 1
            self.uploads -= upload
