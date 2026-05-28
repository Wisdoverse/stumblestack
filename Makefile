# stumblestack dev tasks. Mirrors what CI runs. No wall-clock / RNG in targets
# that produce committed output (the site/index builds are deterministic).
PY ?= python3

.PHONY: help install validate index site eval test lint typecheck check stats clean

help:
	@echo "targets: install validate index site eval test lint typecheck check stats clean"

install:
	$(PY) -m pip install -e mcp-server[dev] -r requirements.txt

validate:
	$(PY) scripts/validate.py

index:
	$(PY) scripts/build_index.py

site:
	$(PY) scripts/build_site.py

eval:
	$(PY) scripts/eval_search.py --min-r10 0.8

test:
	$(PY) -m pytest mcp-server/tests -q

lint:
	ruff check mcp-server/src mcp-server/tests scripts

typecheck:
	mypy --config-file mcp-server/pyproject.toml

# Full local gate — what must pass before a PR.
check: validate index eval test lint
	@echo "all checks passed"

clean:
	rm -rf _site index
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
