PYTHON ?= python

.PHONY: requirements eda evaluate pipeline train predict clean

requirements:
	$(PYTHON) -m pip install -r requirements.txt

eda:
	$(PYTHON) scripts/01_eda.py

evaluate:
	$(PYTHON) scripts/02_evaluate.py

pipeline: eda evaluate
	$(PYTHON) scripts/03_train_and_predict.py

train:
	$(PYTHON) -m campus_energy_forecaster.modeling.train

predict:
	$(PYTHON) -m campus_energy_forecaster.modeling.predict

clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
