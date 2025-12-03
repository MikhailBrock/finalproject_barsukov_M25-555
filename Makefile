.PHONY: install build publish lint format test clean run-parser init-data help

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make run         - Run the application"
	@echo "  make build       - Build package"
	@echo "  make lint        - Check code with ruff"
	@echo "  make format      - Format code with ruff"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean build files"
	@echo "  make init-data   - Initialize data directory"
	@echo "  make help        - Show this help"

install:
	poetry lock
	poetry install

run:
	poetry run valutatrade

build:
	poetry build

publish:
	poetry publish --dry-run

package-install:
	python3 -m pip install dist/*.whl

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

test:
	poetry run python -m pytest

clean:
	rm -rf dist build *.egg-info
	rm -rf logs/*.log
	rm -rf __pycache__ valutatrade_hub/__pycache__ valutatrade_hub/*/__pycache__

run-parser:
	poetry run python -c "from valutatrade_hub.parser_service.updater import RatesUpdater; from valutatrade_hub.parser_service.config import ParserConfig; from valutatrade_hub.parser_service.storage import RatesStorage; config = ParserConfig(); storage = RatesStorage(config); updater = RatesUpdater(config, storage); updater.run_update()"

init-data:
	mkdir -p data logs
	touch data/users.json data/portfolios.json data/rates.json data/exchange_rates.json data/transactions.json
	echo '[]' > data/users.json
	echo '[]' > data/portfolios.json
	echo '{"pairs": {}, "last_refresh": "", "source": "Manual"}' > data/rates.json
	echo '[]' > data/exchange_rates.json
	echo '[]' > data/transactions.json
	@echo "✓ Data directory initialized"

dev:
	poetry run valutatrade --help

all: install init-data