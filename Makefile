.PHONY: install test run lint fmt

install:
	pip install -r requirements.txt

test:
	pytest -q

run:
	uvicorn browser_agent.app:app --reload --host 0.0.0.0 --port 8000

fmt:
	python -m compileall src tests worker alembic

lint:
	python -m compileall src tests worker alembic
