# Makefile for TracePicker project

.PHONY: install test clean lint format run help

# Default target
help:
	@echo "Available targets:"
	@echo "  install     - Install the package in development mode"
	@echo "  test        - Run tests"
	@echo "  clean       - Clean build artifacts"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code with black"
	@echo "  run         - Run TracePicker with default settings"
	@echo "  setup-dev   - Set up development environment"

# Install package in development mode
install:
	pip install -e .

# Install with all dependencies for development
setup-dev:
	pip install -e ".[dev,optimization]"

# Run tests
test:
	python -m pytest tests/ -v

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Run linting
lint:
	flake8 src/ tests/
	mypy src/

# Format code
format:
	black src/ tests/ main.py setup.py

# Run TracePicker with default settings
run:
	python main.py --dataset A --data_dir TracePicker/data

# Run with custom dataset
run-dataset:
	@read -p "Enter dataset name: " dataset; \
	python main.py --dataset $$dataset --data_dir TracePicker/data

# Build package
build:
	python setup.py sdist bdist_wheel

# Install from wheel
install-wheel:
	pip install dist/*.whl
