.PHONY: init deploy down test-e2e test

PYTEST ?= pytest

init:
	git submodule update --init --recursive

deploy:
	docker compose up -d --build

down:
	docker compose down -v

test-e2e:
	$(PYTEST) integration_tests -v

test: test-e2e