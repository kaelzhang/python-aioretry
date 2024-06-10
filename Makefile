files = aioretry test *.py

test:
	pytest -s -v test/test_*.py --doctest-modules --cov aioretry --cov-config=.coveragerc --cov-report term-missing

lint:
	ruff check $(files)

fix:
	ruff check --fix $(files)

install:
	pip install -U .[dev]

report:
	codecov

build: aioretry
	rm -rf dist
	python -m build

publish:
	make build
	twine upload --config-file ~/.pypirc -r pypi dist/*

.PHONY: test build
