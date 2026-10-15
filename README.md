# Linux Performance Telemetry & Bottleneck Analyzer

A Python-based system monitoring tool that collects Linux performance metrics, evaluates system health, identifies potential bottlenecks, and displays results through an interactive dashboard.

## Features

- CPU utilization monitoring
- Memory and swap utilization
- Disk capacity and disk I/O monitoring
- Network throughput monitoring
- System load average
- Top memory-consuming processes
- System health scoring and bottleneck analysis
- SQLite storage for historical snapshots
- Interactive Streamlit dashboard with Plotly charts
- Automated database tests using pytest

## Technology Stack

Python, psutil, Streamlit, Pandas, Plotly, SQLite, pytest, Ubuntu, Linux, and WSL2.

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the analyzer:

```bash
python3 run_analyser.py
```

Launch the dashboard:

```bash
streamlit run dashboard.py --server.port 8502
```

Open http://localhost:8502 in your browser.

## Tests

Run the test suite:

```bash
python3 -m pytest -v
```

The database test suite currently includes tests for database initialization, snapshot storage, snapshot retrieval, and snapshot counting.

## Project Files

- `collector.py` — collects system metrics.
- `Analyser.py` — analyzes metrics and identifies bottlenecks.
- `database.py` — stores and retrieves historical snapshots.
- `reporter.py` — generates a terminal report.
- `run_analyser.py` — runs the analysis workflow.
- `dashboard.py` — displays metrics and historical charts.
- `test_Database.py` — database tests.
- `requirements.txt` — Python dependencies.
- `.gitignore` — excludes generated files and local environment data.

## Future Improvements

- Configurable performance thresholds
- More detailed bottleneck diagnostics
- Historical trend analysis
- Exportable performance reports

## Author

Developed as a Python system monitoring and performance analysis project.