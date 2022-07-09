import asyncio
from functools import cached_property
from collections import defaultdict
from itertools import chain
from urllib.parse import parse_qsl

import aiohttp
from aiohttp import web, WSCloseCode

import logging
log = logging.getLogger(__name__)


class Server():

    def __init__(self, *args, **kwargs):
        """
        Websocket broadcast via http

        ws://host:port/channel_name.ws
        GET /channel_name?message=hello
        POST /channel_name <message=hello>
        GET / (`index.html` for working examples)
        GET / (content-type=application/json) = channelConnections
        """
        self.settings = kwargs
        self.settings.setdefault('listen_only', False)
        self.settings.setdefault('port_tcp', 0)

    @cached_property
    def app(self):
        app = web.Application()

        app['channels'] = defaultdict(set)

        with open('index.html', 'rt', encoding='utf-8') as filehandle:
            self.template_index = filehandle.read()

        app.router.add_get("/", self.handle_index)
        app.router.add_get("/{channel}.ws", self.handle_channel_websocket)
        app.router.add_route("*", "/{channel}", self.handle_channel)
        app.on_startup.append(self.start_background_tasks)
        app.on_shutdown.append(self.on_shutdown)

        return app

    async def start_background_tasks(self, app):
        """
        https://docs.aiohttp.org/en/stable/web_advanced.html#background-tasks
        """
        self.app['tcp_listener'] = asyncio.create_task(self.listen_to_tcp())
    async def listen_to_tcp(self):
        """
        https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-server-using-streams
        """
        port = self.settings.get('port_tcp')
        if not port:
            return
        log.info(f"Serving TCP on {port}")
        server = await asyncio.start_server(self.handle_channel_tcp, '0.0.0.0', port)
        async with server:
            await server.serve_forever()

    async def on_shutdown(self, app):
        for ws in tuple(chain.from_iterable(app['channels'].values())):
            await ws.close(code=WSCloseCode.GOING_AWAY, message='shutdown')

    async def handle_index(self, request):
        if request.headers['accept'].startswith('text/html'):
            return web.Response(text=self.template_index, content_type='text/html')
        data = {
            'channels': {
                channel_name: len(clients)
                for channel_name, clients in request.app['channels'].items()
            },
        }
        return web.json_response(data)

    async def handle_channel(self, request):
        channel_name = request.match_info['channel']
        channel = request.app['channels'][channel_name]
        data = {**dict(parse_qsl(request.query_string)), **await request.post()}
        message = data.get('message', '')
        for client in channel:
            await client.send_str(message)
        return web.json_response({
            'message': message,
            'recipients': len(channel),
        })

    async def handle_channel_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        channel_name = request.match_info['channel']
        log.info(f'websocket onConnected {request.remote=} {channel_name=}')
        channel = request.app['channels'][channel_name]
        channel.add(ws)
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.ERROR:
                    log.error(ws.exception())
                elif self.settings.get('listen_only'):
                    msg_disconnect = 'This service is for listening only'
                    log.warn(f'websocket onMessage {request.remote=} {channel_name=} {msg.data=} - {msg_disconnect}')
                    await ws.send_str(msg_disconnect)
                    await ws.close()
                else:
                    log.debug(f'websocket onMessage {request.remote=} {channel_name=} {msg.data=}')
                    for client in channel:
                        await client.send_str(msg.data)
        finally:
            channel.remove(ws)
            if not channel:
                del request.app['channels'][channel_name]
        log.info(f'websocket onDisconnected {request.remote=} {channel_name=}')
        return ws

    async def handle_channel_tcp(self, reader, writer):
        """
        Inspired by https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-server-using-streams
        """
        class SocketWrapper():  # a duck-type of web.WebSocketResponse()
            def __init__(self, reader, writer):
                self.reader = reader
                self.writer = writer
            async def read(self, *args, **kwargs):
                return await self.reader.read(*args, **kwargs)
            async def send_str(self, data):
                self.writer.write(data.encode())
                self.writer.write(b'\n')  # TODO: is this needed? I needed readline in `client_tcp.py``
                await self.writer.drain()
            async def close(self, code=None, message=None):
                # Todo: finish?
                self.writer.close()  # await?
                #self.reader.close()

        socket = SocketWrapper(reader, writer)
        remote = writer.get_extra_info('peername')
        channel_name = (await socket.read(128)).decode()

        log.info(f'tcp onConnected {remote=} {channel_name=}')
        channel = self.app['channels'][channel_name]
        channel.add(socket)
        while data := await socket.read():  # TODO: do we need readline() here?
            if self.settings.get('listen_only'):
                await socket.send_str('This service is for listening only - closing connection')
                break
            log.info(f'websocket onMessage {remote=} {channel_name=} {data=}')
            for client in channel:
                await client.send_str(data)

        channel.remove(socket)
        if not channel:  # TODO: duplicated logic?
            del self.app['channels'][channel_name]
        await socket.close()
        log.info(f'tcp onDisconnected {remote=} {channel_name=}')


# Main -------------------------------------------------------------------------

def get_args(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog=__name__,
        description="""?""",
    )

    parser.add_argument('--listen_only', action='store_true', help='Any client sending data will be disconnected (default:off)', default=False)
    parser.add_argument('--port_tcp', action='store', type=int, help='', default=0)
    parser.add_argument('--log_level', action='store', type=int, help='loglevel of output to stdout', default=logging.INFO)

    args = parser.parse_args(argv)
    return vars(args)


def aiohttp_app(argv):
    # python3 -m aiohttp.web -H 0.0.0.0 -P 9800 server:aiohttp_app
    options = get_args(argv)
    log.setLevel(options['log_level'])
    return Server(**options).app
