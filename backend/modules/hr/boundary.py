"""Apply private headers even to denied requests and limit HR JSON bodies."""
from starlette.responses import JSONResponse


class HRBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        protected = path == '/people/hr' or path.startswith(('/api/hr/', '/hr/'))
        if scope['type'] != 'http' or not protected:
            return await self.app(scope, receive, send)

        async def private_send(message):
            if message['type'] == 'http.response.start':
                headers = dict(message.get('headers', []))
                headers.update({b'cache-control': b'no-store', b'pragma': b'no-cache',
                                b'x-content-type-options': b'nosniff', b'referrer-policy': b'no-referrer',
                                b'x-frame-options': b'SAMEORIGIN'})
                if b'content-security-policy' not in headers:
                    headers[b'content-security-policy'] = (b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                                          b"img-src 'self' blob:; object-src 'none'; base-uri 'none'; "
                                                          b"form-action 'self'; frame-ancestors 'self'")
                message['headers'] = list(headers.items())
            await send(message)

        # Multipart is deliberately unused; raw document uploads enforce their
        # own streamed limit. JSON is bounded before FastAPI/Pydantic parse it.
        headers = dict(scope.get('headers', []))
        if b'application/json' in headers.get(b'content-type', b''):
            body = bytearray()
            while True:
                part = await receive()
                if part['type'] == 'http.disconnect':
                    return
                body.extend(part.get('body', b''))
                if len(body) > 128 * 1024:
                    return await JSONResponse({'detail': 'Požadavek je příliš velký.'}, status_code=413)(scope, receive, private_send)
                if not part.get('more_body', False):
                    break
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()
            return await self.app(scope, replay, private_send)
        return await self.app(scope, receive, private_send)
