.PHONY: test demo golden check

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

demo:
	PYTHONPATH=src python3 -m grid_ops_arena demo --output-dir reports

golden:
	PYTHONPATH=src python3 -m grid_ops_arena demo --output-dir artifacts/demo

check:
	python3 -m compileall -q src tests
