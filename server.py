import asyncio
from functools import cached_property
from collections import defaultdict
from itertools import chain
from urllib.parse import parse_qsl
from functools import partial
from typing import NamedTuple
import re
import operator
from types import SimpleNamespace

import aiohttp
from aiohttp import web, WSCloseCode

import logging
log = logging.getLogger(__name__)

class PortChannelMapping(NamedTuple):
    port: int
    channel: str
    @classmethod
    def parse(cls, port_channel_mapping):
        """
        >>> PortChannelMapping.parse("8001:test1")
        PortChannelMapping(port=8001, channel='test1')
        >>> PortChannelMapping.parse("8001")
        PortChannelMapping(port=8001, channel='8001')
        >>> PortChannelMapping.parse("test1")
        Traceback (most recent call last):
        AttributeError: ...
        """
        port, channel = re.match(r'(?P<port>\d+)(?::(?P<channel>.*))?', port_channel_mapping).groups()
        return cls(int(port), channel or str(port))

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
        self.settings.setdefault('tcp', ())
        self.settings.setdefault('udp', ())

    @cached_property
    def app(self):
        app = web.Application()

        app['channels'] = defaultdict(set)

        with open('index.html', 'rt', encoding='utf-8') as filehandle:
            self.template_index = filehandle.read()

        app.router.add_get("/", self.handle_index)
        app.router.add_get("/{channel}.ws", self.handle_channel_websocket)
        app.router.add_route("*", "/{channel}", self.handle_channel_http)
        app.on_startup.append(self.start_background_tasks)
        app.on_shutdown.append(self.on_shutdown)

        return app

    # Startup ------------------------------------------------------------------

    async def start_background_tasks(self, app):
        """
        https://docs.aiohttp.org/en/stable/web_advanced.html#background-tasks
        """
        self.app['listeners_tcp']     = tuple(asyncio.create_task(self.listen_to_tcp(tcp)) for tcp in self.settings['tcp'])

        self.app['udp_message_queue'] = asyncio.Queue()  # https://stackoverflow.com/a/53724990/3356840
        self.app['event_udp']         = asyncio.create_task(self.handle_channel_udp())
        self.app['listeners_udp']     = tuple(asyncio.create_task(self.listen_to_udp(udp)) for udp in self.settings['udp'])


    # Shutdown -----------------------------------------------------------------

    async def on_shutdown(self, app):
        for ws in tuple(chain.from_iterable(app['channels'].values())):
            await ws.close(code=WSCloseCode.GOING_AWAY, message='shutdown')

    # Index --------------------------------------------------------------------

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

    # Echo Logic - TODO abstract out into mixin? or function? ----------

    def channel(self, channel_name):
        return self.app['channels'][channel_name]

    async def onClientConnect(self, channel_name, client):
        channel = self.channel(channel_name)
        _len = len(channel)
        channel.add(client)
        if len(channel) > _len:
            log.info(f'onClientConnect {channel_name=} {client.__class__} {client.addr=}')
    async def onClientDisconnect(self, channel_name, client):
        channel = self.channel(channel_name)
        channel.remove(client)
        log.info(f'onDisconnect {channel_name=} {client.__class__} {client.addr=}')
        if not channel:
            log.info(f'Channel removed {channel_name=}')
            del self.app['channels'][channel_name]
        

    async def onReceive(self, channel_name, data, data_type, from_client):
        log.debug(f'onReceive {channel_name=} {from_client.addr=} {data_type=} {data=}')
        # TODO: listen_only?
        match data_type:
            case aiohttp.WSMsgType.TEXT:
                _send = operator.attrgetter('send_str')
            case aiohttp.WSMsgType.BINARY:
                _send = operator.attrgetter('send_bytes')
            case _:
                _send = None
        for client in self.channel(channel_name):
            await _send(client)(data)


    # HTTP ---------------------------------------------------------------------

    async def handle_channel_http(self, request):
        channel_name = request.match_info['channel']
        channel = self.channel(channel_name)
        data = {**dict(parse_qsl(request.query_string)), **await request.post()}
        message = data.get('message', '') # TODO: body in binary?
        await self.onReceive(channel_name, message, data_type=aiohttp.WSMsgType.TEXT, from_client=SimpleNamespace(addr=request.remote))
        return web.json_response({
            'message': message,
            'recipients': len(channel),
        })

    # Websocket ----------------------------------------------------------------

    async def handle_channel_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        setattr(ws, 'addr', ws._req.remote)
        channel_name = request.match_info['channel']
        await self.onClientConnect(channel_name, ws)
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.ERROR:
                    log.error(ws.exception())
                # TODO: move to recv?
                elif self.settings.get('listen_only'):
                    msg_disconnect = 'This service is for listening only'
                    log.warn(f'websocket onMessage {ws.addr=} {channel_name=} {msg.data=} - {msg_disconnect}')
                    await ws.send_str(msg_disconnect)
                    await ws.close()
                elif msg.type in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                    await self.onReceive(channel_name, data=msg.data, data_type=msg.type, from_client=ws)
        finally:
            await self.onClientDisconnect(channel_name, ws)
        return ws  # TODO: is this needed?


    # TCP ----------------------------------------------------------------------

    async def listen_to_tcp(self, port_channel_mapping):
        """
        https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-server-using-streams
        """
        log.info(f"Serving TCP on {port_channel_mapping=}")
        server = await asyncio.start_server(partial(self.handle_channel_tcp, port_channel_mapping.channel), '0.0.0.0', port_channel_mapping.port)
        async with server:
            await server.serve_forever()


    async def handle_channel_tcp(self, channel_name, reader, writer):
        """
        Inspired by https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-server-using-streams
        """
        class TcpResponse():  # a duck-type of web.WebSocketResponse()
            def __init__(self, reader, writer):
                self.reader = reader
                self.writer = writer
                self.addr = self.writer.get_extra_info('peername')
            async def read(self, *args, **kwargs):
                return await self.reader.read(*args, **kwargs)
            async def send_str(self, data):
                self.writer.write(data.encode())
                self.writer.write(b'\n')  # TODO: is this needed? I needed readline in `client_tcp.py``
                await self.writer.drain()
            async def send_bytes(self, data):
                self.writer.write(data)
                await self.writer.drain()
            async def close(self, code=None, message=None):
                # Todo: finish?
                self.writer.close()  # await?
                #self.reader.close()

        client = TcpResponse(reader, writer)
        await self.onClientConnect(channel_name, client)
        while data := await client.read():  # TODO: do we need readline() here?
            # TODO: listen_only move to recv?
            if self.settings.get('listen_only'):
                await client.send_str('This service is for listening only - closing connection')
                break
            await self.onReceive(channel_name, data, aiohttp.WSMsgType.BINARY, client)

        await self.onClientDisconnect(channel_name, client)
        await client.close()


    # UDP ----------------------------------------------------------------------

    async def listen_to_udp(self, port_channel_mapping):
        """
        https://docs.python.org/3/library/asyncio-protocol.html#udp-echo-server
        https://stackoverflow.com/a/64540509/3356840
        """
        log.info(f"Serving UDP on {port_channel_mapping=}")
        class UdpResponse():
            def __init__(self, addr, transport):
                self.addr = addr
                self.transport = transport
            def __eq__(self, other):
                return isinstance(other, self.__class__) and self.addr[0] == other.addr[0]
            def __hash__(self):
                return hash(self.addr[0])
            async def read(self, *args, **kwargs):
                raise NotImplementedError()
            async def send_str(self, data):
                await self.send_bytes(data.encode('utf8'))
            async def send_bytes(self, data):
                self.transport.sendto(data, self.addr)  # TODO: test this?
            async def close(self, *args, **kwargs):
                self.transport.close()
        class UdpReceiver(asyncio.DatagramProtocol):
            def __init__(self, queue, channel_name):
                self.queue = queue
                self.channel_name = channel_name
            def connection_made(self, transport):
                self.transport = transport
            def datagram_received(self, data, addr):
                self.queue.put_nowait((data, self.channel_name, UdpResponse(addr, self.transport)))
        transport, protocol = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: UdpReceiver(self.app['udp_message_queue'], port_channel_mapping.channel), 
            local_addr=('0.0.0.0', port_channel_mapping.port),
        )

    async def handle_channel_udp(self):
        """
        https://stackoverflow.com/questions/53733140/how-to-use-udp-with-asyncio-for-multiple-file-transfer-from-server-to-client-p
        """
        log.info("Starting udp queue listener")
        queue = self.app['udp_message_queue']
        while True:
            data, channel_name, client = await queue.get()  # block=True, timeout=1
            await self.onClientConnect(channel_name, client)
            await self.onReceive(channel_name, data, aiohttp.WSMsgType.BINARY, client)



# Main -------------------------------------------------------------------------

def get_args(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog=__name__,
        description="""?""",
    )

    parser.add_argument('--listen_only', action='store_true', help='Any client sending data will be disconnected (default:off)', default=False)
    parser.add_argument('--tcp', action='store', nargs="*", type=PortChannelMapping.parse, help='e.g. 8001:test1')
    parser.add_argument('--udp', action='store', nargs="*", type=PortChannelMapping.parse, help='')
    parser.add_argument('--log_level', action='store', type=int, help='loglevel of output to stdout', default=logging.INFO)

    args = parser.parse_args(argv)
    return vars(args)


def aiohttp_app(argv):
    # python3 -m aiohttp.web -H 0.0.0.0 -P 9800 server:aiohttp_app
    options = get_args(argv)
    log.setLevel(options['log_level'])
    return Server(**options).app
