FROM python:alpine as base

WORKDIR /server

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

FROM base as code
    COPY \
        __init__.py \
        server.py \
        index.html \
    ./

# Test -------------------------------------------------------------------------

FROM base as base_test
    COPY requirements.test.txt .
    RUN pip3 install --no-cache-dir -r requirements.test.txt
    FROM base_test as test
    COPY --from=code /server/ /server/
    COPY tests/* ./tests/
    RUN pytest

# Prod -------------------------------------------------------------------------

FROM code as production
EXPOSE 9800
EXPOSE 9801
EXPOSE 9802
ENTRYPOINT ["python3", "-m", "aiohttp.web", "-H", "0.0.0.0", "-P", "9800", "server:aiohttp_app"]
CMD []
# Cant use ENV variables in CMD. Maybe we could use ARGS?

# TODO: Healthcheck could actually use Python client to route ping-pong messages?
#COPY client_healthcheck.py ./
HEALTHCHECK --interval=15s --timeout=1s --retries=3 --start-period=1s \
    CMD netstat -an | grep ${PORT} > /dev/null; if [ 0 != $? ]; then exit 1; fi;
