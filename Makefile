PYTHON ?= python

.PHONY: requirements train predict clean

requirements:
	$(PYTHON) -m pip install -r requirements.txt

train:
	$(PYTHON) -m campus_energy_forecaster.modeling.train

predict:
	$(PYTHON) -m campus_energy_forecaster.modeling.predict

clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
