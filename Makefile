VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

install:
	python -m venv $(VENV)
	$(PIP) install -r requirements.txt

test-run:
	$(PY) optech_fr.py batch --min-date 2022-07-01 --limit 3 --oldest-first

full-run:
	$(PY) optech_fr.py batch --min-date 2022-07-01 --oldest-first

single:
	$(PY) optech_fr.py latest
