"""Private fleet responses and a bounded command body."""
from starlette.responses import JSONResponse


class FleetBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        private = path == '/fleet' or path.startswith(('/fleet/', '/api/fleet/'))
        if scope['type'] != 'http' or not private:
            return await self.app(scope, receive, send)

        async def private_send(message):
            if message['type'] == 'http.response.start':
                headers = [(k, v) for k, v in message.get('headers', []) if k.lower() != b'cache-control']
                headers.extend([(b'cache-control', b'no-store, private'), (b'x-content-type-options', b'nosniff'),
                                (b'x-frame-options', b'DENY'), (b'referrer-policy', b'no-referrer')])
                message = dict(message, headers=headers)
            await send(message)

        if scope['method'] == 'POST' and path.startswith('/api/fleet/'):
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                body.extend(message.get('body', b''))
                if len(body) > 16384:
                    return await JSONResponse({'detail': 'Požadavek je příliš velký.'}, status_code=413)(scope, receive, private_send)
                if not message.get('more_body', False):
                    break
            delivered = False

            async def replay_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()

            return await self.app(scope, replay_receive, private_send)
        await self.app(scope, receive, private_send)
