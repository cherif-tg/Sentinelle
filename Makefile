.PHONY: install test lint ingest-dry demo notebooks api dashboard up down

install:
	uv pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check src tests dashboard

ingest-dry:
	python -m sentinelle_lome.ingestion.gee_export --dry-run

demo:
	python -m sentinelle_lome.pipeline.gold

notebooks:
	jupyter nbconvert --to notebook --execute --inplace notebooks/0*.ipynb

api:
	uvicorn sentinelle_lome.serving.api:app --reload --port 8000

dashboard:
	streamlit run dashboard/app.py

up:
	docker compose up -d

down:
	docker compose down
