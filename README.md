# FX Option Risk Pricer

Small production-style CLI for FX option pricing and Greek risk reports. The tool reads position data from CSV, validates inputs, prices each option with the Garman-Kohlhagen model, and writes timestamped CSV reports.

This project is intentionally compact, but it is structured like an internal platform utility rather than a one-off notebook or ad hoc script.

## What It Shows

- Python package structure with a console entry point
- Input validation for market data and position files
- Garman-Kohlhagen pricing for FX calls and puts
- Delta, gamma, vega, theta, and notional value output
- Timestamped report generation for repeatable review
- Unit tests for pricing and CSV ingestion
- Dockerfile for repeatable execution
- GitHub Actions workflow for pull-request validation

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
fx-risk-pricer --input data/example_positions.csv --stdout
```

Reports are written to `reports/` by default.

## Run With Docker

```bash
docker build -t fx-option-risk-pricer .
docker run --rm fx-option-risk-pricer
```

## Input Format

```csv
symbol,spot,strike,maturity,r_dom,r_for,vol,type,notional
EURUSD,1.10,1.15,0.25,0.02,0.01,0.12,call,1000000
USDJPY,135.00,130.00,0.50,0.015,0.005,0.10,put,500000
```

## Repository Layout

```text
fx_option_risk_pricer/
  cli.py       Console entry point and report writer
  io.py        CSV loading and validation
  models.py    Typed position and result models
  pricing.py   Garman-Kohlhagen pricing logic
data/
  example_positions.csv
tests/
  test_io.py
  test_pricing.py
```
