# FX Option Risk Pricer

This is a basic Python script that calculates the fair value and risk metrics (delta and vega) for FX options using the Garman-Kohlhagen model. It reads input positions from a CSV file and outputs a timestamped CSV risk report.

## What It Does

- Loads FX option positions from a CSV
- Prices each option using interest rate-adjusted Black-Scholes (Garman-Kohlhagen)
- Calculates delta and vega for each option
- Outputs the results to a CSV in the /reports folder

## How to Run

1. Install dependencies:

   ```bash
   pip install pandas scipy
   ```

2. Prepare your input CSV in the `data/` folder (see example below).

3. Run the script:

   ```bash
   python fx_risk_dashboard.py
   ```

4. Output will be saved in the `reports/` folder with a timestamped filename.

## Sample Input Format

File: `data/example_positions.csv`

```csv
symbol,spot,strike,maturity,r_dom,r_for,vol,type
EURUSD,1.10,1.15,0.25,0.02,0.01,0.12,call
USDJPY,135.00,130.00,0.50,0.015,0.005,0.10,put
GBPUSD,1.25,1.30,0.20,0.018,0.008,0.11,call
```

## Output

A CSV file like:

```csv
symbol,price,delta,vega
EURUSD,0.0234,0.4412,7.1230
USDJPY,1.8923,-0.5813,52.0894
GBPUSD,0.0191,0.4070,6.9951
```

## Next Steps (Ideas for Improvement)

- Build a real-time web dashboard using Streamlit or Dash
- Add more Greeks (gamma, theta)
- Load live market data from an API
- Include a basic backtesting engine for historical PnL
- Package into a CLI tool or Docker container
- Add unit tests (pytest) and CI pipeline

## Project Structure

```
fx-risk-dashboard/
├── fx_risk_dashboard.py
├── data/
│   └── example_positions.csv
├── reports/
└── README.txt
```
