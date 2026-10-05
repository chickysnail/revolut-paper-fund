# Paper fund tracker

Imaginary equal-weight, buy-and-hold fund of 20 stocks (not a real investment).
`tracker.py` runs daily via `.github/workflows/track.yml` and commits
`README.md`, `fund_chart.png`, `fund_history.csv` (all generated, don't edit by hand).

- `portfolio.csv`: tickers, start date (2026-10-05), optional start price.
  Empty start price = first close on/after start date, or the latest available
  close if the start date has no close yet.
- Fund value = mean of (price / start_price) * 100, starts at 100.
- `python tracker.py --demo` uses fake data and writes to `demo_out/` (gitignored, never commit).

## Revolut forecast snapshots

`revolut_forecast_YYYY-MM-DD.csv` = what Revolut promised on that date. The whole
point of the project is to compare these promises with what actually happened.

- Source: Revolut app, Investment page, stock suggestions. Copied by hand by the owner.
- `expected_return_pct`: Revolut's expected return per stock. Revolut does not
  state the horizon; we ASSUME 12 months (typical for analyst price targets).
- `risk`: Revolut's own risk label.
- Snapshots are immutable. If Revolut shows new numbers, add a new file with the
  new date; never edit or overwrite an old one.
- `tracker.py` uses the earliest snapshot (the one matching the fund start) for
  the "Revolut forecast vs actual" section in README.md.
