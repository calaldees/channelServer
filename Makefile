CONTAINER_TAG=websocket_echo_server

.PHONY: help
.DEFAULT_GOAL:=help
help:	## display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2 } END{print ""}' $(MAKEFILE_LIST)

DOCKER_RUN:=docker run -it --rm -p 9800:9800 -p 9801:9801 -p 9802:9802/udp

build:  ##
	docker build --tag ${CONTAINER_TAG} .
run: build  ## run service from container
	${DOCKER_RUN} ${CONTAINER_TAG} \
		--log_level=10 --tcp 9801:test1 --udp 9802:test1
shell:  ## shell into container for development
	${DOCKER_RUN} --volume ${PWD}/channel_server:/channel_server/channel_server --no-healthcheck --entrypoint /bin/sh ${CONTAINER_TAG}
test:
	docker build --tag ${CONTAINER_TAG} --target test .

local_run:  ##
	uv run --module aiohttp.web -H 0.0.0.0 -P 9800 channel_server.channel_server:aiohttp_app \
		--log_level=10 --tcp 9801:test1 --udp 9802:test1
local_test:  ##
	uv run -m pytest

clean:  ## Delete temp files and containers
	docker rmi ${CONTAINER_TAG}
	rm -rf __pycache__ .pytest_cache uv.lock .venv
