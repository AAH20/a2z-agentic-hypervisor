.PHONY: test bench wheel clean

test:
	python3 -m unittest discover tests

bench:
	python3 benchmarks/run_hypervisor_bench.py

wheel:
	rm -rf dist build *.egg-info
	python3 -c "import setuptools.build_meta as b; b.build_wheel('dist')"

clean:
	rm -rf dist build *.egg-info .pytest_cache __pycache__ */__pycache__ */*!/__pycache__
