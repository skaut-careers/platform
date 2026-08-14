.PHONY: install web-install web-build serve web-dev dev test test-llm typecheck web-typecheck web-lint web-test check

# Convenience wrappers — underlying tools are poetry / pnpm / uvicorn.

install: web-install
	poetry install

web-install:
	pnpm --dir web install

web-build:
	pnpm --dir web build

serve:
	poetry run uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000

web-dev:
	pnpm --dir web dev

# API + Next.js together (Ctrl+C stops both).
dev:
	@trap 'kill 0' EXIT; \
	$(MAKE) serve & \
	$(MAKE) web-dev & \
	wait

test:
	poetry run pytest

test-llm:
	poetry run pytest -m llm -s

typecheck:
	poetry run pyright

web-typecheck:
	pnpm --dir web exec tsc --noEmit

web-lint:
	pnpm --dir web lint

web-test:
	pnpm --dir web test

check: typecheck test web-typecheck web-lint web-test
