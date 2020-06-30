channelServer
=============

A [python](https://python.org) [aiohttp](https://docs.aiohttp.org/) based echo server with channel support

```bash
    make run  # for docker
    python3 -m aiohttp.web -H 0.0.0.0 -P 9800 server:aiohttp_app --log_level=10
    python3 -m webbrowser -t "http://localhost:9800/"
```

Visit [http://localhost:9800/](http://localhost:9800/)

The websocket channels can be sent messages from GET or POST requests
Option to `--listen_only`
