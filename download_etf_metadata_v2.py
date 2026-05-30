# %% [markdown]
# # EMEA ETF Metadata (v2)
#
# Same as `download_etf_metadata.py` but uses a local, patched `get_etf_overview`
# that handles **both** justETF HTML templates:
#
# | Template | Example | Basic data source |
# |---|---|---|
# | Old (Wicket) | `LU1772333404` | `<table>` rows |
# | New | `FR0011871110` | `data-testid="tl_etf-basics_value_*"` |
#
# The pip-installed `justetf_scraping.etf_profile.get_etf_overview` only handles the
# old template; all basic fields return `None` for new-template ETFs.

# %%
import json
import re
import time
from pathlib import Path
from typing import List, Optional, TypedDict
from xml.etree import ElementTree

import pandas as pd
import requests
from bs4 import BeautifulSoup

import justetf_scraping  # still used for load_overview screener data

# %% [markdown]
# ## Patched `get_etf_overview`

# %%

# ── Type definitions ──────────────────────────────────────────────────────────

class AllocationItem(TypedDict):
    name: str
    percentage: float

class HoldingItem(TypedDict):
    name: str
    percentage: float
    isin: Optional[str]

class EtfOverview(TypedDict):
    isin: str
    name: Optional[str]
    description: Optional[str]
    index: Optional[str]
    investment_focus: Optional[str]
    fund_size_eur: Optional[float]
    ter: Optional[float]
    replication: Optional[str]
    legal_structure: Optional[str]
    strategy_risk: Optional[str]
    sustainability: Optional[bool]
    fund_currency: Optional[str]
    currency_hedged: Optional[bool]
    volatility_1y: Optional[float]
    inception_date: Optional[str]
    distribution_policy: Optional[str]
    distribution_frequency: Optional[str]
    fund_domicile: Optional[str]
    fund_provider: Optional[str]
    top_holdings: List[HoldingItem]
    countries: List[AllocationItem]
    sectors: List[AllocationItem]
    holdings_date: Optional[str]
    gettex: None


# ── Constants ─────────────────────────────────────────────────────────────────

_BASE_URL = "https://www.justetf.com/en/etf-profile.html"
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_percentage(value: str) -> Optional[float]:
    if not value:
        return None
    m = re.search(r"([\d.]+)\s*%", value)
    return float(m.group(1)) if m else None


def _parse_fund_size(value: str) -> Optional[float]:
    if not value:
        return None
    m = re.search(r"([\d,]+)\s*m", value, re.I)
    return float(m.group(1).replace(",", "")) if m else None


def _parse_date(value: str) -> Optional[str]:
    return value.replace("As of ", "").strip() if value else None


# ── Template detection ────────────────────────────────────────────────────────

def _is_new_template(soup: BeautifulSoup) -> bool:
    """New template uses tl_etf-basics_value_* testids; old template uses table rows."""
    return soup.find(attrs={"data-testid": "tl_etf-basics_value_index-name"}) is not None


# ── Basic-data extraction: new template ──────────────────────────────────────

_NEW_TEMPLATE_FIELD_MAP = {
    "index-name":            "Index",
    "investment-focus":      "Investment focus",
    "ter":                   "Total expense ratio",
    "replication":           "Replication",
    "legal-structure":       "Legal structure",
    "strategy-risk":         "Strategy risk",
    "sustainable":           "Sustainability",
    "fund-currency":         "Fund currency",
    "currency-hedge":        "Currency risk",
    "volatility":            "Volatility 1 year (in EUR)",
    "launch-date":           "Inception/ Listing Date",
    "distribution-policy":   "Distribution policy",
    "distribution-interval": "Distribution frequency",
    "domicile-country":      "Fund domicile",
    "fund-provider":         "Fund Provider",
}


def _extract_basic_data_new_template(soup: BeautifulSoup) -> dict:
    data = {}
    for suffix, canonical_key in _NEW_TEMPLATE_FIELD_MAP.items():
        elem = soup.find(attrs={"data-testid": f"tl_etf-basics_value_{suffix}"})
        if elem:
            data[canonical_key] = elem.get_text(strip=True)

    # Fund size: lives in the row text as "Fund sizeEUR 1,098 m"
    fund_size_row = soup.find(attrs={"data-testid": "etf-basics_row_fund-size"})
    if fund_size_row:
        label_elem = fund_size_row.find(attrs={"data-testid": "etf-basics_label_fund-size"})
        label = label_elem.get_text(strip=True) if label_elem else "Fund size"
        val = fund_size_row.get_text(strip=True).replace(label, "", 1).strip()
        if val:
            data["Fund size"] = val

    return data


# ── Basic-data extraction: old template ──────────────────────────────────────

_OLD_TEMPLATE_EXPECTED_KEYS = {
    "Fund size", "Total expense ratio", "Replication",
    "Fund currency", "Fund domicile", "Legal structure",
    "Distribution policy", "Investment focus",
}


def _extract_basic_data_old_template(soup: BeautifulSoup) -> dict:
    for table in soup.find_all("table"):
        data = {}
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                data[cells[0].get_text(strip=True)] = cells[1].get_text(strip=True)
        if _OLD_TEMPLATE_EXPECTED_KEYS & set(data.keys()):
            return data
    return {}


# ── AJAX helpers ──────────────────────────────────────────────────────────────

def _fetch_ajax_data(session: requests.Session, isin: str, endpoint: str) -> Optional[str]:
    ajax_url = f"{_BASE_URL}?0-1.0-{endpoint}&isin={isin}&_wicket=1"
    ajax_headers = {
        **_DEFAULT_HEADERS,
        "X-Requested-With": "XMLHttpRequest",
        "Wicket-Ajax": "true",
        "Wicket-Ajax-BaseURL": f"en/etf-profile.html?isin={isin}",
        "Accept": "application/xml, text/xml, */*; q=0.01",
        "Referer": f"{_BASE_URL}?isin={isin}",
    }
    try:
        resp = session.get(ajax_url, headers=ajax_headers)
        if resp.status_code == 200 and resp.text:
            if "access-denied" in resp.text or "internal-error" in resp.text:
                return None
            return resp.text
    except Exception as e:
        print(f"    AJAX error ({endpoint}): {e}")
    return None


def _parse_allocation_from_ajax(
    xml_response: str, table_testid: str, name_testid: str, pct_testid: str
) -> List[AllocationItem]:
    allocations: List[AllocationItem] = []
    try:
        root = ElementTree.fromstring(xml_response)
        for component in root.findall(".//component"):
            html_content = component.text
            if not html_content or f'data-testid="{table_testid}"' not in html_content:
                continue
            soup = BeautifulSoup(html_content, "html.parser")
            for row in soup.find_all("tr", attrs={"data-testid": True}):
                name_elem = row.find("td",   attrs={"data-testid": name_testid})
                pct_elem  = row.find("span", attrs={"data-testid": pct_testid})
                if name_elem and pct_elem:
                    name = name_elem.get_text(strip=True)
                    pct  = _parse_percentage(pct_elem.get_text(strip=True))
                    if name and pct is not None:
                        allocations.append(AllocationItem(name=name, percentage=pct))
            break
    except Exception as e:
        print(f"    Allocation AJAX parse error: {e}")
    return allocations


def _parse_allocation_from_soup(
    soup: BeautifulSoup, row_testid: str, name_testid: str, pct_testid: str
) -> List[AllocationItem]:
    allocations: List[AllocationItem] = []
    for row in soup.find_all("tr", attrs={"data-testid": row_testid}):
        name_elem = row.find("td",   attrs={"data-testid": name_testid})
        pct_elem  = row.find("span", attrs={"data-testid": pct_testid})
        if name_elem and pct_elem:
            name = name_elem.get_text(strip=True)
            pct  = _parse_percentage(pct_elem.get_text(strip=True))
            if name and pct is not None:
                allocations.append(AllocationItem(name=name, percentage=pct))
    return allocations


def _get_allocations(
    session, soup, isin, expand,
    ajax_endpoint, table_testid, name_testid, pct_testid, row_testid,
) -> List[AllocationItem]:
    if expand:
        xml = _fetch_ajax_data(session, isin, ajax_endpoint)
        if xml:
            return _parse_allocation_from_ajax(xml, table_testid, name_testid, pct_testid)
    return _parse_allocation_from_soup(soup, row_testid, name_testid, pct_testid)


# ── Main function ─────────────────────────────────────────────────────────────

def get_etf_overview(
    isin: str,
    include_gettex: bool = True,
    expand_allocations: bool = True,
) -> EtfOverview:
    """
    Patched version of justetf_scraping.etf_profile.get_etf_overview.

    Handles both justETF HTML templates (old Wicket and new React-style),
    so ETFs like FR0011871110 return populated basic-data fields instead of all None.
    """
    session = requests.Session()
    response = session.get(f"{_BASE_URL}?isin={isin}", headers=_DEFAULT_HEADERS)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch ETF page for {isin}: HTTP {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    new_template = _is_new_template(soup)

    # Description
    desc_elem = soup.find("div", attrs={"data-testid": "etf-quote-section_description-label"})
    description = desc_elem.get_text(strip=True) if desc_elem else None

    # Name
    name = None
    if new_template:
        name_elem = soup.find(attrs={"data-testid": "etf-profile-header_etf-name"})
        if name_elem:
            name = name_elem.get_text(strip=True)
    if not name:
        title_elem = soup.find("title")
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            if "|" in title_text:
                name = title_text.split("|")[0].strip()

    # Basic data
    basic_data = (
        _extract_basic_data_new_template(soup)
        if new_template else
        _extract_basic_data_old_template(soup)
    )

    # Top holdings
    top_holdings: List[HoldingItem] = []
    for row in soup.find_all("tr", attrs={"data-testid": "etf-holdings_top-holdings_row"}):
        name_elem = row.find("a",    attrs={"data-testid": "tl_etf-holdings_top-holdings_link_name"})
        pct_elem  = row.find("span", attrs={"data-testid": "tl_etf-holdings_top-holdings_value_percentage"})
        if name_elem and pct_elem:
            holding_name = name_elem.get_text(strip=True)
            pct = _parse_percentage(pct_elem.get_text(strip=True))
            href = name_elem.get("href", "")
            holding_isin = href.split("/stock-profiles/")[-1] if "/stock-profiles/" in href else None
            if holding_name and pct is not None:
                top_holdings.append(HoldingItem(name=holding_name, percentage=pct, isin=holding_isin))

    # Countries & sectors
    countries = _get_allocations(
        session, soup, isin, expand_allocations,
        "holdingsSection-countries-loadMoreCountries",
        "etf-holdings_countries_table",
        "tl_etf-holdings_countries_value_name",
        "tl_etf-holdings_countries_value_percentage",
        "etf-holdings_countries_row",
    )
    sectors = _get_allocations(
        session, soup, isin, expand_allocations,
        "holdingsSection-sectors-loadMoreSectors",
        "etf-holdings_sectors_table",
        "tl_etf-holdings_sectors_value_name",
        "tl_etf-holdings_sectors_value_percentage",
        "etf-holdings_sectors_row",
    )

    # Holdings date
    ref_date_elem = soup.find("div", attrs={"data-testid": "tl_etf-holdings_reference-date"})
    holdings_date = _parse_date(ref_date_elem.get_text(strip=True)) if ref_date_elem else None

    return EtfOverview(
        isin=isin,
        name=name,
        description=description,
        index=basic_data.get("Index"),
        investment_focus=basic_data.get("Investment focus"),
        fund_size_eur=_parse_fund_size(basic_data.get("Fund size")),
        ter=_parse_percentage(basic_data.get("Total expense ratio")),
        replication=basic_data.get("Replication"),
        legal_structure=basic_data.get("Legal structure"),
        strategy_risk=basic_data.get("Strategy risk"),
        sustainability=basic_data.get("Sustainability", "").lower() == "yes",
        fund_currency=basic_data.get("Fund currency"),
        currency_hedged=basic_data.get("Currency risk", "").lower() != "currency unhedged",
        volatility_1y=_parse_percentage(basic_data.get("Volatility 1 year (in EUR)")),
        inception_date=basic_data.get("Inception/ Listing Date"),
        distribution_policy=basic_data.get("Distribution policy"),
        distribution_frequency=basic_data.get("Distribution frequency"),
        fund_domicile=basic_data.get("Fund domicile"),
        fund_provider=basic_data.get("Fund Provider"),
        top_holdings=top_holdings,
        countries=countries,
        sectors=sectors,
        holdings_date=holdings_date,
        gettex=None,
    )


# %% [markdown]
# ## 1. Load ETF list and filter for EMEA

# %%
etf_list = pd.read_excel("../etf_list.xlsx", header=1)
print(f"Total ETFs in list: {len(etf_list)}")
etf_list.head(3)

# %%
emea_df = etf_list[etf_list["Region"] == "EMEA"].copy()
print(f"EMEA ETF rows: {len(emea_df)}")

emea_isins = emea_df["ISIN"].dropna().unique().tolist()
print(f"Unique EMEA ISINs: {len(emea_isins)}")
print("First 5:", emea_isins[:5])

# %% [markdown]
# ## 2. Pull screener overview data for all EMEA ISINs

# %%
print("Loading justETF screener overview (all ETFs)...")
all_overview_df = justetf_scraping.load_overview(enrich=True)
print(f"Total ETFs in screener: {len(all_overview_df)}  |  Columns: {list(all_overview_df.columns)}")

# %%
screener_emea = all_overview_df[all_overview_df.index.isin(emea_isins)].copy()
print(f"Matched {len(screener_emea)} of {len(emea_isins)} EMEA ISINs in screener")
screener_emea.head(3)

# %% [markdown]
# ## 3. Pull profile-page metadata for each ISIN

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
        for k, v in screener_row.items():
            if pd.isna(v) if not isinstance(v, (list, dict)) else False:
                screener_row[k] = None
            elif hasattr(v, "isoformat"):
                screener_row[k] = v.isoformat()
            elif hasattr(v, "item"):
                screener_row[k] = v.item()
    else:
        screener_row = {}
        print(f"  [{isin}] not found in screener data")

    # --- Profile page data (patched get_etf_overview) ---
    try:
        profile = get_etf_overview(isin, include_gettex=False, expand_allocations=True)
        profile_dict = dict(profile)
        profile_dict.pop("gettex", None)
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
    time.sleep(1.0)

print(f"\nDone. Saved {len(profiles)} ETFs. Profile failures: {len(failed_profile)}")
if failed_profile:
    print("Failed ISINs:", failed_profile)

# %% [markdown]
# ## 4. Build a flat summary DataFrame and save as CSV

# %%
def flatten_for_csv(record: dict) -> dict:
    """Serialise list/dict values to JSON strings for CSV compatibility."""
    flat = {}
    for k, v in record.items():
        flat[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
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
print(f"ISINs requested : {len(emea_isins)}")
print(f"ISINs saved     : {len(profiles)}")
print(f"In screener     : {len(screener_emea)}")
print(f"Profile failures: {len(failed_profile)}")
print()

print("Columns in summary CSV:")
for col in summary_df.columns:
    non_null = summary_df[col].notna().sum()
    print(f"  {col:<45} {non_null}/{len(summary_df)} non-null")

# %%
sample_isin = emea_isins[0]
print(f"Sample record for {sample_isin}:")
sample = profiles[sample_isin].copy()
for key in ("top_holdings", "countries", "sectors"):
    if key in sample and isinstance(sample[key], list):
        sample[key] = sample[key][:3]
print(json.dumps(sample, indent=2, default=str))
