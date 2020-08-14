
async def handle_channel_tcp(self, reader, writer):
    """
    Unfinished concept to handle plain TCP connections
    Inspired by https://asyncio.readthedocs.io/en/latest/tcp_echo.html
    """
    class SocketWrapper():
        def __init__(self, reader, writer):
            self.reader = reader
            self.writer = writer
        async def read(self, *args, **kwargs):
            return self.reader.read(*args, **kwargs)
        async def send_str(self, data):
            self.writer.write(data)
            await self.writer.drain()
    socket = SocketWrapper(reader, writer)
    remote = writer.get_extra_info('peername')
    channel_name = (await socket.read(128)).decode()
    log.info(f'tcp onConnected {remote=} {channel_name=}')
    channel = self.app['channels'][channel_name]
    channel.add(socket)
    while data := await socket.read():
        if self.settings.get('listen_only'):
            await socket.send_str('This service is for listening only - closing connection')
            break
        log.info(f'websocket onMessage {remote=} {channel_name=} {data=}')
        for client in channel:
            await client.send_str(data)
    log.info(f'tcp onDisconnected {remote=} {channel_name=}')
    writer.close()
