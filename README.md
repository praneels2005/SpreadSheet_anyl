## Trading Performance & Reconciliation Pipeline

This repository assembles multiple trading data sources into a reconciled workbook and an interactive Streamlit dashboard for monitoring options performance and risk. The pipeline combines a manually maintained challenge ledger, a normalized sheet of supplemental trades, and a broker activity export, then reconciles them per ticker to produce portfolio-level KPIs.

### Repository Contents

- `Spread_Anyl.ipynb` – end-to-end reconciliation that builds the consolidated `TradingMasterData.xlsx` workbook. It cleans challenge data, parses broker activities, matches trades, and summarizes gains per ticker. 【F:Spread_Anyl.ipynb†L885-L2478】
- `Mahe_Normalization.ipynb` – normalizes the supplemental `Mahe-Challenge-Copy - ChallengeCopy.csv` into the canonical schema expected by the main pipeline. 【F:Mahe_Normalization.ipynb†L1105-L1806】
- `TradingMasterData.xlsx` – pipeline output with a summary tab (`Ticker Info`) and per-ticker detail tabs created by `Spread_Anyl.ipynb`.
- `trading_dashboard.py` – Streamlit app for visualizing PnL, win/loss stats, concentration risk, and ticker-level breakdowns from the `Ticker Info` tab. 【F:trading_dashboard.py†L1-L134】
- Raw inputs: `25KChallenge.csv`, `Mahe-Challenge-Copy - ChallengeCopy.csv`, `Tradier_activities_2025-05-11_2025-08-14.csv` (and its duplicate `activities_2025-08-14.csv`), plus the normalized `Mahe-Challenge.csv`.

### Data Flow at a Glance

1. **Normalize supplemental trades** (`Mahe_Normalization.ipynb`)
   - Reads `Mahe-Challenge-Copy - ChallengeCopy.csv`.
   - Standardizes date formatting (`Trade Enter`, `Trade Exit`, `Exp Date`), renames columns, and converts numeric fields to currency strings before writing `Mahe-Challenge.csv`. 【F:Mahe_Normalization.ipynb†L1105-L1808】

2. **Ingest the challenge ledger** (`Spread_Anyl.ipynb`)
   - Loads `25KChallenge.csv`, promotes the first data row to headers, adds an `Index`, and trims to the core trading columns (`Ticker`, `Trade Enter/Exit`, `Strike`, `C/P`, `Exp Date`, `Initial Contracts`, `$ Gain`). 【F:Spread_Anyl.ipynb†L885-L950】
   - Normalizes dates to month abbreviations with year rollovers for expirations, and cleans nested values in `Trade Exit`. 【F:Spread_Anyl.ipynb†L885-L1146】

3. **Parse broker activity exports**
   - Filters out $0 amounts, extracts tickers from the option symbols, derives strike/expiry/call-put from descriptions, and renames columns to the shared schema. Positive `Initial Contracts` are treated as openings; negatives are closings with `Trade Exit` populated. 【F:Spread_Anyl.ipynb†L1156-L1280】

4. **Combine data sources**
   - Appends the normalized `Mahe-Challenge.csv` rows to the challenge ledger to keep a single canonical table (`Dates`). 【F:Spread_Anyl.ipynb†L2047-L2071】

5. **Reconcile per ticker**
   - Builds dictionaries keyed by ticker for both ledger and broker data.
   - `trade_comparisons` aligns trades by `Trade Enter`, `Strike`, `C/P`, and `Exp Date`, then optionally matches exit dates to link closings back to openings. 【F:Spread_Anyl.ipynb†L2165-L2193】

6. **Write the consolidated workbook**
   - For each ticker:
     - Creates a worksheet with broker rows first (most recent on top), then ledger rows.
     - Inserts subtotals: `Gain_Sum` (ledger `$ Gain`), total broker `Amount`, calculated PnL per 25k-share sizing, and contract counts via Excel formulas.
     - Highlights key cells with conditional fill for quick auditing.
   - The `Ticker Info` tab stores one row per ticker with three metrics:
     - `Master Gain`: Sum of ledger `$ Gain` for that ticker.
     - `Total Gain`: Sum of broker `Amount` for that ticker (linked via worksheet formulas).
     - `Calc Gain`: Size-adjusted PnL using the calculated gain cells in each ticker tab.
   - Final rows on `Ticker Info` aggregate portfolio totals for all three metrics. 【F:Spread_Anyl.ipynb†L2241-L2478】

7. **Visualize results**
   - `trading_dashboard.py` loads the `Ticker Info` sheet, computes total/average PnL, win rate, profit factor, and concentration metrics, and renders Streamlit dashboards:
     - **Overview**: headline KPIs, insight callouts, and PnL by ticker.
     - **Ticker view**: per-ticker contribution and rankings.
     - **Risk view**: cumulative absolute PnL contribution and top-3 concentration alerting.
     - **Audit view**: missing-value counts and descriptive statistics for `Master Gain`, `Total Gain`, and `Calc Gain`. 【F:trading_dashboard.py†L28-L134】

### Domain Notes & Quality Guardrails

- **Options context**: `C/P` distinguishes calls vs puts; `Strike` is currency formatted; `Exp Date` may roll into the following year if the expiry precedes the entry month/day.
- **Contract sign convention**: Positive `Initial Contracts` represent openings (buys) while negatives represent exits (sells); the broker parser sets `Trade Exit` for closing legs to tie them back to opens. 【F:Spread_Anyl.ipynb†L1156-L1280】
- **Currency handling**: Ledger values arrive as strings with `$` and commas; the reconciliation strips formatting for math, then writes user-friendly currency strings back into Excel.
- **Data hygiene**: Broker rows with zero `Amount` are dropped, and malformed `Trade Exit` values are coerced to `NaN` to avoid false matches. 【F:Spread_Anyl.ipynb†L1156-L1200】
- **Risk interpretation**: The dashboard’s concentration view operates on absolute PnL, so large losses still contribute to “risk share” even if net PnL is positive.

### Running the Pipeline

1. **Set up Python dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Regenerate normalized inputs (optional)**
   - Execute `Mahe_Normalization.ipynb` to refresh `Mahe-Challenge.csv` if the source CSV changes. Example:
   ```bash
   jupyter nbconvert --to notebook --execute Mahe_Normalization.ipynb
   ```

3. **Build the consolidated workbook**
   - Run `Spread_Anyl.ipynb` after updating any raw inputs to produce a fresh `TradingMasterData.xlsx`:
   ```bash
   jupyter nbconvert --to notebook --execute Spread_Anyl.ipynb
   ```
   - Verify the `Ticker Info` tab populates `Master Gain`, `Total Gain`, and `Calc Gain` for every ticker.

4. **Launch the dashboard**
   ```bash
   streamlit run trading_dashboard.py
   ```
   - Upload `TradingMasterData.xlsx` (or a CSV export of `Ticker Info`) when prompted. The app derives all visuals from `Master Gain`, `Total Gain`, and `Calc Gain`, plus ticker names.

### Extending or Debugging

- **Adding new data sources**: Normalize to the canonical columns (`Index`, `Ticker`, `Trade Enter`, `Trade Exit`, `Exp Date`, `Strike`, `C/P`, `Initial Contracts`, `$ Gain`, `Amount`, `Symbol`) before concatenation into `Dates`.
- **Improving matching logic**: `trade_comparisons` currently keys on entry date, strike, call/put, and expiry. Consider adding cost/quantity thresholds or ISIN/OSM identifiers for tighter reconciliations if broker exports include them.
- **Testing scenarios**: Use tickers with mixed opens/closes and partial fills to validate that contract summations (`SUM(G...)`) and PnL formulas (`SUM(J...)` and calc gain) remain consistent.
