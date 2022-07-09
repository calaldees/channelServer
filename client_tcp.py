import asyncio

import logging
log = logging.getLogger(__name__)


# https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-client-using-streams
async def listen_tcp(host=None, port=None, channel=None, **options):
    log.info(f'tcp connect {host=} {port=} {channel=}')
    reader, writer = await asyncio.open_connection(host, port)
    writer.write(channel.encode())

    while data := await reader.readline():
        print(data.decode().strip())

    log.info(f'tcp disconnect')
    #reader.close()
    writer.close()


# Main -------------------------------------------------------------------------

def get_args(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog=__name__,
        description="""?""",
    )

    parser.add_argument('--host', action='store', help='', default='localhost')
    parser.add_argument('--port', action='store', type=int, help='', default=9801)
    parser.add_argument('--channel', action='store', help='', default='test')
    parser.add_argument('--log_level', action='store', type=int, help='loglevel of output to stdout', default=logging.WARNING)

    args = parser.parse_args(argv)
    return vars(args)

if __name__ == "__main__":
    options = get_args()
    logging.basicConfig(level=options['log_level'])

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(listen_tcp(**options))
    except KeyboardInterrupt:
        pass
    #loop.run_until_complete(asyncio.sleep(2))  # Zero-sleep to allow underlying connections to close
    loop.close()
