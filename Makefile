PYTHON ?= python3
JOBS ?= 4

.PHONY: setup fetch masters font web release all test qa qa-external clean clean-all

setup:
	$(PYTHON) -m pip install -e '.[dev]'

fetch:
	$(PYTHON) -m jinjer_sans.build fetch

masters:
	$(PYTHON) -m jinjer_sans.build masters

font:
	$(PYTHON) -m jinjer_sans.build font

web:
	$(PYTHON) -m jinjer_sans.build web --jobs $(JOBS)

release:
	$(PYTHON) -m jinjer_sans.build release

all:
	$(PYTHON) -m jinjer_sans.build all --jobs $(JOBS)

test:
	$(PYTHON) -m pytest

qa:
	$(PYTHON) -m jinjer_sans.qa

qa-external:
	$(PYTHON) -m jinjer_sans.qa --external

clean:
	$(PYTHON) -m jinjer_sans.build clean

clean-all:
	$(PYTHON) -m jinjer_sans.build clean --upstream
