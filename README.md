channelServer
=============

A [python](https://python.org) [aiohttp](https://docs.aiohttp.org/) based echo server with multiple channels. Bridging: WebSockets, HTTP(Post/Get), TCP, UDP. I wanted a universal way of connecting things to other things for teaching/learning activities.

* Cloud Base IDE (will auto launch server)
    * [GitHub CodeSpaces](https://codespaces.new/calaldees/channelServer?quickstart=1)
    * [GitPod](https://gitpod.io#https://github.com/calaldees/channelServer)
* Locally
    *   ```bash
        make      # display help
        make run  # with docker
        ```
* Visit [http://localhost:9800/](http://localhost:9800/) for html debugging/testing/example

* Features
    * Can bridge/communicate over `WebSockets`, `TCP` and `UDP`
    * The channels can be sent messages from `GET` or `POST` requests (see index.html help)
    * Option to use websockets to `--listen_only`


Future Development Ideas
------------------------

* UDP Bridge
    * refine responses to a udp client?
* Hierarchy of channel names and propagation
    * Way of joining as a 'privileged' user to have echo powers. All other users send only to privileged user.
    * /test1/test2/
        * test1 can see all test1 and test2 messages (as test2 is a child of test1)
        * test2 can only see test2 messages
    * channel names have `up_only` or `peers`?

References and Other
------

* [Using local services in Gitpod](https://www.gitpod.io/blog/local-services-in-gitpod)
    * How to connect GitPod to ports on your local machine


Similar Projects
----------------

* [chisel](https://www.gitdetail.com/repositories/gitpod-io/chisel/306427) - A fast TCP/UDP tunnel over HTTP