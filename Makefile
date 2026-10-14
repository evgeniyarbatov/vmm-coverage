DATA_DIR ?= $(HOME)/Documents/data/vmm-coverage
GPX ?=
PORT ?= 8000

.DEFAULT_GOAL := help

.PHONY: setup lock test lint fetch run serve help

setup:
	uv sync --group dev

lock:
	uv lock

test:
	uv run python -m unittest discover -s tests -v

lint:
	uv run ruff check .

fetch:
	DATA_DIR=$(DATA_DIR) uv run python -m scripts.fetch_opencellid
	DATA_DIR=$(DATA_DIR) uv run python -m scripts.fetch_osm

run:
	DATA_DIR=$(DATA_DIR) uv run python -m scripts.run $(if $(GPX),--gpx $(GPX),)

serve:
	cd site && python3 -m http.server $(PORT)

help:
	@echo "setup    - uv sync --group dev"
	@echo "lock     - uv lock"
	@echo "test     - unittest, no network, no API keys"
	@echo "lint     - ruff check"
	@echo "fetch    - download/refresh cell + OSM data into DATA_DIR (needs OPENCELLID_API_KEY)"
	@echo "run      - gpx -> sample -> join towers -> report (offline, GPX=path to override course)"
	@echo "serve    - serve site/ locally at http://localhost:PORT (default 8000)"
	@echo "DATA_DIR = $(DATA_DIR)"
