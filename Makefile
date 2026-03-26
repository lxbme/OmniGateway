.PHONY: init deploy down test-e2e test pull

PYTEST ?= pytest

init:
	git submodule update --init --recursive

pull:
	git pull origin main
	git submodule update --recursive

deploy:
	docker compose up -d --build

down:
	docker compose down -v

test-e2e:
	$(PYTEST) integration_tests -v

test: test-e2e