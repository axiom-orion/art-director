.PHONY: setup test lint eval gallery shots demo clean

setup:
	python -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check src eval scripts tests

eval:
	python eval/run_eval.py

gallery:
	python scripts/build_gallery.py

shots:
	python scripts/shoot_gallery.py

demo:
	python -m art_director "a calm fintech app for nurses" --html gallery/demo.html

clean:
	rm -rf gallery/*.html .pytest_cache **/__pycache__ *.egg-info src/*.egg-info
