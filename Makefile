PYTHON ?= python

.PHONY: requirements data analysis test web clean

requirements:
	$(PYTHON) -m pip install -r requirements.txt pytest

data:
	$(PYTHON) scripts/download_data.py

analysis:
	$(PYTHON) scripts/run_analysis.py

test:
	$(PYTHON) -m pytest -q

web:
	cd web && npm install && npm run dev
