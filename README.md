channelServer
=============

A [python](https://python.org) [aiohttp](https://docs.aiohttp.org/) based echo server with multiple channels. Bridging: WebSockets, HTTP(Post/Get), TCP, UDP. I wanted a universal way of connecting things to other things for teaching/learning activities.

* [Start server with GitPod](https://gitpod.io#https://github.com/calaldees/channelServer)
* Start locally
    * ```bash
        make run  # with docker
        ```

See `Makefile` for running locally by typing `make`

Visit [http://localhost:9800/](http://localhost:9800/) for html debugging/testing/example

The channels can be sent messages from GET or POST requests
Option to `--listen_only`

Ideas
-----

* UDP Bridge
    * maybe a port mapped to a channel_name?
* Hierarchy of channel names and propagation
    * Way of joining as a 'privileged' user to have echo powers. All other users send only to privileged user.
    * /test1/test2/
        * test1 can see all test1 and test2 messages (as test2 is a child of test1)
        * test2 can only see test2 messages
    * channel names have `up_only` or `peers`?