FROM python:alpine AS base
    COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/
#FROM ghcr.io/astral-sh/uv:python3.14-alpine as base
    ENV UV_SYSTEM_PYTHON=1

    WORKDIR /channel_server

    COPY pyproject.toml .
    RUN uv sync --no-dev

FROM base AS code
    COPY ./channel_server/ ./channel_server/

FROM base AS test
    RUN uv sync
    COPY --from=code /channel_server/ .
    COPY tests/* ./tests/
    RUN uv run -m pytest

FROM code AS production
    EXPOSE 9800
    EXPOSE 9801
    EXPOSE 9802
    ENTRYPOINT ["uv", "run", "--no-sync", "--module", "aiohttp.web", "-H", "0.0.0.0", "-P", "9800", "channel_server.channel_server:aiohttp_app"]
    CMD []
    # Cant use ENV variables in CMD. Maybe we could use ARGS?

    # TODO: Healthcheck could actually use Python client to route ping-pong messages?
    #COPY client_healthcheck.py ./
    HEALTHCHECK --interval=15s --timeout=1s --retries=3 --start-period=1s \
        CMD netstat -an | grep ${PORT} > /dev/null; if [ 0 != $? ]; then exit 1; fi;
