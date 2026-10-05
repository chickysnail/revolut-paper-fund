"""Equal-weight, buy-and-hold paper fund tracker. See README.md for output."""
import argparse
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
PERIODS = [  # label, offset
    ("1 day", None),
    ("1 week", pd.DateOffset(weeks=1)),
    ("1 month", pd.DateOffset(months=1)),
    ("3 months", pd.DateOffset(months=3)),
    ("6 months", pd.DateOffset(months=6)),
]


def fetch_prices(tickers, start, retries=4):
    import yfinance as yf

    last = None
    for attempt in range(retries):
        try:
            df = yf.download(
                tickers, start=start, auto_adjust=True, progress=False, threads=False
            )
            if df is not None and not df.empty:
                close = df["Close"]
                if isinstance(close, pd.Series):
                    close = close.to_frame(tickers[0])
                return close
            last = RuntimeError("Yahoo returned no data")
        except Exception as e:  # network errors, rate limits
            last = e
        wait = 2 ** (attempt + 1)
        print(f"fetch attempt {attempt + 1} failed ({last}); retrying in {wait}s", file=sys.stderr)
        time.sleep(wait)
    raise SystemExit(f"FAILED to fetch prices from Yahoo: {last}")


def demo_prices(tickers, start):
    rng = np.random.default_rng(42)
    idx = pd.bdate_range(start, pd.Timestamp.today().normalize())
    steps = rng.normal(0.0005, 0.02, size=(len(idx), len(tickers)))
    return pd.DataFrame(100 * np.exp(np.cumsum(steps, axis=0)), index=idx, columns=tickers)


def build_fund(prices, pf):
    """Return (normalized per-stock df, fund series). Fails loudly on missing data."""
    prices = prices.sort_index()
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    norm = {}
    for _, r in pf.iterrows():
        t = r["ticker"]
        if t not in prices.columns or prices[t].dropna().empty:
            raise SystemExit(f"No price data for {t}")
        s = prices[t].loc[prices.index >= pd.Timestamp(r["start_date"])].dropna()
        if s.empty:
            raise SystemExit(f"No price for {t} on/after {r['start_date']}")
        sp = r["start_price"] if pd.notna(r["start_price"]) else s.iloc[0]
        norm[t] = s / sp * 100
    norm = pd.DataFrame(norm).sort_index().ffill()
    missing = norm.columns[norm.isna().any()].tolist()
    if missing:
        raise SystemExit(f"Gaps in data (stock not trading yet?): {missing}")
    return norm, norm.mean(axis=1)


def returns_table(fund):
    last_date, last = fund.index[-1], fund.iloc[-1]
    rows = []
    for label, off in PERIODS:
        if off is None:
            if len(fund) < 2:
                continue
            base = fund.iloc[-2]
        else:
            target = last_date - off
            if fund.index[0] > target:
                continue
            base = fund.loc[:target].iloc[-1]
        rows.append((label, last / base - 1))
    rows.append(("Since start", last / 100 - 1))
    return rows


def make_chart(norm, fund, path):
    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
    for t in norm.columns:
        ax.plot(norm.index, norm[t], color="grey", alpha=0.25, lw=0.8)
    ax.plot(fund.index, fund.values, color="tab:blue", lw=3, label="Fund")
    ax.axhline(100, color="black", ls="--", lw=1)
    ax.set_title("Paper fund (equal weight, start = 100)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def pct(x):
    return f"{x * 100:+.2f}%"


def write_readme(path, norm, fund, demo):
    last_date = fund.index[-1].date()
    since = (norm.iloc[-1] / 100 - 1).sort_values()
    lines = []
    if demo:
        lines += ["**DEMO DATA - not real**", ""]
    lines += [
        "# Paper fund tracker",
        "",
        "![chart](fund_chart.png)",
        "",
        f"**Fund value: {fund.iloc[-1]:.2f}** (as of {last_date}, start = 100)",
        "",
        "| Period | Return |",
        "|---|---|",
    ]
    lines += [f"| {l} | {pct(v)} |" for l, v in returns_table(fund)]
    lines += ["", "**Best 3 since start**", ""]
    lines += [f"- {t}: {pct(v)}" for t, v in since[::-1].head(3).items()]
    lines += ["", "**Worst 3 since start**", ""]
    lines += [f"- {t}: {pct(v)}" for t, v in since.head(3).items()]
    lines += ["", "_Imaginary equal-weight buy-and-hold fund, not a real investment._", ""]
    Path(path).write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="fake data, writes to demo_out/")
    args = ap.parse_args()

    pf = pd.read_csv(ROOT / "portfolio.csv", dtype={"start_date": str})
    out = ROOT
    if args.demo:
        out = ROOT / "demo_out"
        out.mkdir(exist_ok=True)
        pf["start_date"] = (pd.Timestamp.today() - pd.Timedelta(days=400)).strftime("%Y-%m-%d")
        pf["start_price"] = np.nan
        prices = demo_prices(pf["ticker"].tolist(), pf["start_date"].iloc[0])
    else:
        prices = fetch_prices(pf["ticker"].tolist(), pf["start_date"].min())

    norm, fund = build_fund(prices, pf)
    fund.rename("fund_value").round(4).to_csv(out / "fund_history.csv", index_label="date")
    make_chart(norm, fund, out / "fund_chart.png")
    write_readme(out / "README.md", norm, fund, args.demo)
    print(f"Fund value {fund.iloc[-1]:.2f} on {fund.index[-1].date()} -> {out}")


if __name__ == "__main__":
    main()
