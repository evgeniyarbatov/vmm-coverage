DATA_DIR ?= $(HOME)/Documents/data/vmm-coverage
GPX ?=

.PHONY: install lock test lint fetch run clean help

install:
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

clean:
	rm -f $(DATA_DIR)/samples.json $(DATA_DIR)/cells.json $(DATA_DIR)/gaps.json
	rm -f docs/coverage.csv docs/coverage.gpx docs/coverage.geojson docs/gaps.json docs/summary.md

help:
	@echo "install  - uv sync --group dev"
	@echo "lock     - uv lock"
	@echo "test     - unittest, no network, no API keys"
	@echo "lint     - ruff check"
	@echo "fetch    - download/refresh cell + OSM data into DATA_DIR (needs OPENCELLID_API_KEY)"
	@echo "run      - gpx -> sample -> join towers -> report (offline, GPX=path to override course)"
	@echo "clean    - remove derived JSON/CSV/GPX, keep downloaded tower DB"
	@echo "DATA_DIR = $(DATA_DIR)"
