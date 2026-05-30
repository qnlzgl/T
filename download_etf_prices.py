# %% [markdown]
# # EMEA ETF Historic Price Data
# Reads EMEA ETFs from `etf_list.xlsx`, pulls historic price data via `justetf_scraping`, and saves each ETF's data as a CSV in `etf-data/`.

# %%
import time
from pathlib import Path

import pandas as pd

import justetf_scraping

# %% [markdown]
# ## 1. Load ETF list and filter for EMEA

# %%
# The xlsx has a title row at index 0; actual headers are at row 1
etf_list = pd.read_excel("../etf_list.xlsx", header=1)
print(f"Total ETFs in list: {len(etf_list)}")
etf_list.head(3)

# %%
emea_df = etf_list[etf_list["Region"] == "EMEA"].copy()
print(f"EMEA ETF rows: {len(emea_df)}")
emea_df.head(3)

# %%
# Deduplicate by ISIN and drop rows without a valid ISIN
emea_isins = emea_df["ISIN"].dropna().unique().tolist()
print(f"Unique EMEA ISINs: {len(emea_isins)}")
print(emea_isins[:5])

# %% [markdown]
# ## 2. Pull historic price data and save to etf-data/

# %%
OUTPUT_DIR = Path("../etf-data")
OUTPUT_DIR.mkdir(exist_ok=True)

charts = {}
failed = []

for i, isin in enumerate(emea_isins):
    out_path = OUTPUT_DIR / f"{isin}.csv"
    if out_path.exists():
        print(f"[{i+1}/{len(emea_isins)}] {isin} — already exists, loading from disk")
        charts[isin] = pd.read_csv(out_path, index_col="date", parse_dates=True)
        continue

    try:
        df = justetf_scraping.load_chart(isin, currency="GBP")
        df.to_csv(out_path)
        charts[isin] = df
        print(f"[{i+1}/{len(emea_isins)}] {isin} — {len(df)} rows saved")
    except Exception as e:
        print(f"[{i+1}/{len(emea_isins)}] {isin} — FAILED: {e}")
        failed.append(isin)

    # Be polite to the API
    time.sleep(0.5)

print(f"\nDone. Fetched {len(charts)} ETFs. Failed: {len(failed)}")
if failed:
    print("Failed ISINs:", failed)

# %% [markdown]
# ## 3. Quick inspection of results

# %%
# Show a summary of all fetched charts
summary = pd.DataFrame(
    [
        {
            "isin": isin,
            "rows": len(df),
            "start_date": df.index.min(),
            "end_date": df.index.max(),
            "latest_quote": df["quote"].iloc[-1],
        }
        for isin, df in charts.items()
    ]
).set_index("isin")

print(f"Summary ({len(summary)} ETFs):")
summary

# %%
# Preview one chart
sample_isin = emea_isins[0]
print(f"Sample: {sample_isin}")
charts[sample_isin].tail()


