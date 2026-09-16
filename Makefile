.PHONY: install test integration lint package api sample benchmark

install:
	python -m pip install --requirement requirements-dev.lock
	python -m pip install --no-deps --no-build-isolation -e .

test:
	pytest -m "not integration" --cov=data_quality_pipeline --cov-report=term-missing

integration:
	pytest -m integration

lint:
	ruff check .

package:
	python -m build --no-isolation

api:
	uvicorn data_quality_pipeline.api:app --reload

sample:
	python scripts/generate_synthetic_data.py --rows 10000 --output sample_data/customers.csv

benchmark:
	python scripts/run_benchmark.py --rows 100000 --repeats 3
