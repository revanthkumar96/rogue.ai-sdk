.PHONY: build upload clean

build:
	rm -rf dist rouge.egg-info/
	python -m build

upload:
	twine check dist/*
	twine upload dist/*

clean:
	rm -rf dist rouge.egg-info/
