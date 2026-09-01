FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY fx_option_risk_pricer ./fx_option_risk_pricer
COPY data ./data
RUN pip install --no-cache-dir .

ENTRYPOINT ["fx-risk-pricer"]
CMD ["--input", "data/example_positions.csv", "--stdout"]
