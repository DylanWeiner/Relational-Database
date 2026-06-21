.PHONY: all setup build run clean

# Default target — running plain `make` does this
all: setup build run

# Create a virtual environment and install dependencies
setup:
# 	source .venv/bin/activate

# Build/rebuild the database from raw data
build:
	python load_data.py

# Launch the dashboard
run:
	streamlit run app.py

# Remove the generated database and virtual environment
clean:
	rm -f cell-database.db