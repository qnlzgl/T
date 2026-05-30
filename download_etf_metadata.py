# %% [markdown]
# # EMEA ETF Metadata
# 
# Reads EMEA ETFs from `etf_list.xlsx`, pulls metadata from two justETF sources:
# 1. **Overview/screener data** (`justetf_scraping.load_overview`) — 46 fields including TER, size, returns, volatility, replication method, etc.
# 2. **Profile page data** (`justetf_scraping.etf_profile.get_etf_overview`) — detailed fields: description, index tracked, top holdings, country/sector allocations.
# 
# Each ETF's merged metadata is saved as `etf-metadata-gbp/<ISIN>.json`.
# A combined flat summary is also saved as `etf-metadata-gbp/emea_metadata_summary.csv`.

# %%
import json
import time
from pathlib import Path

import pandas as pd

import justetf_scraping
from justetf_scraping.etf_profile import get_etf_overview

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

# Deduplicate by ISIN and drop rows without a valid ISIN
emea_isins = emea_df["ISIN"].dropna().unique().tolist()
print(f"Unique EMEA ISINs: {len(emea_isins)}")
print("First 5:", emea_isins[:5])

# %% [markdown]
# ## 2. Pull screener overview data for all EMEA ISINs
# 
# `load_overview()` hits the justETF screener API and returns one row per ETF with ~46 columns.

# %%
print("Loading justETF screener overview (all ETFs)...")
all_overview_df = justetf_scraping.load_overview(enrich=True)
print(f"Total ETFs in screener: {len(all_overview_df)}  |  Columns: {list(all_overview_df.columns)}")

# %%
# Filter screener data to our EMEA ISINs
# The screener DataFrame is indexed by ISIN
screener_emea = all_overview_df[all_overview_df.index.isin(emea_isins)].copy()
print(f"Matched {len(screener_emea)} of {len(emea_isins)} EMEA ISINs in screener")
screener_emea.head(3)

# %% [markdown]
# ## 3. Pull profile-page metadata for each ISIN
# 
# `get_etf_overview()` scrapes the individual ETF profile page for richer data:
# description, index tracked, top holdings, country and sector allocations.
# We disable the live gettex WebSocket quote (`include_gettex=False`) since we only need static metadata.

# %%
OUTPUT_DIR = Path("../etf-metadata-gbp")
OUTPUT_DIR.mkdir(exist_ok=True)

profiles = {}
failed_profile = []

for i, isin in enumerate(emea_isins):
    out_path = OUTPUT_DIR / f"{isin}.json"

    if out_path.exists():
        print(f"[{i+1}/{len(emea_isins)}] {isin} — already exists, loading from disk")
        with open(out_path) as f:
            profiles[isin] = json.load(f)
        continue

    # --- Screener data for this ISIN ---
    if isin in screener_emea.index:
        screener_row = screener_emea.loc[isin].to_dict()
        # Convert any non-JSON-serialisable types (Timestamp, numpy types, NaN)
        for k, v in screener_row.items():
            if pd.isna(v) if not isinstance(v, (list, dict)) else False:
                screener_row[k] = None
            elif hasattr(v, "isoformat"):        # Timestamp
                screener_row[k] = v.isoformat()
            elif hasattr(v, "item"):             # numpy scalar
                screener_row[k] = v.item()
    else:
        screener_row = {}
        print(f"  [{isin}] not found in screener data")

    # --- Profile page data ---
    try:
        profile = get_etf_overview(isin, include_gettex=False, expand_allocations=True)
        # Convert dataclass/TypedDict to plain dict; drop the live quote key
        profile_dict = dict(profile)
        profile_dict.pop("gettex", None)  # exclude live quote (not metadata)
    except Exception as e:
        print(f"[{i+1}/{len(emea_isins)}] {isin} — profile FAILED: {e}")
        profile_dict = {}
        failed_profile.append(isin)

    # --- Merge: screener fields + profile fields (profile wins on overlap) ---
    merged = {"isin": isin, **screener_row, **profile_dict}
    profiles[isin] = merged

    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2, default=str)

    print(f"[{i+1}/{len(emea_isins)}] {isin} — saved ({len(merged)} fields)")

    # Polite delay between profile page requests
    time.sleep(1.0)

print(f"\nDone. Saved {len(profiles)} ETFs. Profile failures: {len(failed_profile)}")
if failed_profile:
    print("Failed ISINs:", failed_profile)

# %% [markdown]
# ## 4. Build a flat summary DataFrame and save as CSV
# 
# Nested fields (`top_holdings`, `countries`, `sectors`) are serialised to JSON strings so the CSV stays flat.

# %%
def flatten_for_csv(record: dict) -> dict:
    """Serialise list/dict values to JSON strings for CSV compatibility."""
    flat = {}
    for k, v in record.items():
        if isinstance(v, (list, dict)):
            flat[k] = json.dumps(v)
        else:
            flat[k] = v
    return flat

rows = [flatten_for_csv(profiles[isin]) for isin in emea_isins if isin in profiles]
summary_df = pd.DataFrame(rows).set_index("isin")

csv_path = OUTPUT_DIR / "emea_metadata_summary.csv"
summary_df.to_csv(csv_path)
print(f"Summary CSV saved: {csv_path}")
print(f"Shape: {summary_df.shape}")
summary_df.head(3)

# %% [markdown]
# ## 5. Quick inspection

# %%
# Coverage stats
print(f"ISINs requested : {len(emea_isins)}")
print(f"ISINs saved     : {len(profiles)}")
print(f"In screener     : {len(screener_emea)}")
print(f"Profile failures: {len(failed_profile)}")
print()

# Column overview
print("Columns in summary CSV:")
for col in summary_df.columns:
    non_null = summary_df[col].notna().sum()
    print(f"  {col:<45} {non_null}/{len(summary_df)} non-null")

# %%
# Preview one JSON record
sample_isin = emea_isins[0]
print(f"Sample record for {sample_isin}:")
sample = profiles[sample_isin].copy()
# Truncate long lists for display
for key in ("top_holdings", "countries", "sectors"):
    if key in sample and isinstance(sample[key], list):
        sample[key] = sample[key][:3]
print(json.dumps(sample, indent=2, default=str))


