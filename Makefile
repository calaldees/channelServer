CONTAINER_TAG=websocket_echo_server

.PHONY: help
.DEFAULT_GOAL:=help
help:	## display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2 } END{print ""}' $(MAKEFILE_LIST)

DOCKER_RUN:=docker run -it --rm -p 9800:9800 -p 9801:9801

build:  ##
	docker build --tag ${CONTAINER_TAG} .
run: build  ## run service from container
	${DOCKER_RUN} ${CONTAINER_TAG} --log_level=10 --port_tcp 9801

shell:  ## shell into container for development
	${DOCKER_RUN} --volume ${PWD}:/server/ --no-healthcheck --entrypoint /bin/bash ${CONTAINER_TAG}

local_install:  ##
	pip3 install -r requirements.txt
	pip3 install -r requirements.test.txt
local_run:  ##
	python3 -m aiohttp.web -H 0.0.0.0 -P 9800 server:aiohttp_app --log_level=10 --port_tcp 9801
local_test:  ##
	pytest

clean:  ## Delete temp files and containers
	docker rmi ${CONTAINER_TAG}
	rm -rf __pycache__
