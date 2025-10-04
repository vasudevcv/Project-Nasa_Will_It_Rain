# ParadeGuard Makefile

.PHONY: install test run clean

# Install dependencies
install:
	pip install -r requirements.txt

# Test installation
test:
	python test_installation.py

# Run the Streamlit app
run:
	streamlit run app/app.py

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Help
help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies"
	@echo "  make test     - Test installation"
	@echo "  make run      - Run the Streamlit app"
	@echo "  make clean    - Clean up cache files"
	@echo "  make help     - Show this help"
