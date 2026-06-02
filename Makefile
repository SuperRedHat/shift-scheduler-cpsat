.PHONY: demo test install clean

install:         ## Install OR-Tools + pytest
	pip install -r requirements.txt

demo:            ## Run the scheduler demo (optimal + infeasibility + benchmark)
	python demo.py

test:            ## Run the invariant test suite
	python -m pytest -q

clean:
	rm -rf .pytest_cache **/__pycache__
