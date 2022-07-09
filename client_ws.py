import asyncio
import aiohttp

import logging
log = logging.getLogger(__name__)


async def listen_websocket(url):
    async with aiohttp.ClientSession() as session:
        log.info(f'websocket connect {url=}')
        async with session.ws_connect(url) as ws:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.ERROR:
                    break
                print(msg.data)
        await session.close()


# Main -------------------------------------------------------------------------

def get_args(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog=__name__,
        description="""?""",
    )

    parser.add_argument('--url', action='store', help='', default='ws://localhost:9800/test.ws')
    parser.add_argument('--log_level', action='store', type=int, help='loglevel of output to stdout', default=logging.WARNING)

    args = parser.parse_args(argv)
    return vars(args)

if __name__ == "__main__":
    options = get_args()
    logging.basicConfig(level=options['log_level'])

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(listen_websocket(options['url']))
    except KeyboardInterrupt:
        pass
    #loop.run_until_complete(asyncio.sleep(2))  # Zero-sleep to allow underlying connections to close
    loop.close()
