# helper_lib/xbrl.py

import requests
import pandas as pd
from .utils import SEC_HEADERS, normalize_cik


# ==========================================================
# ⭐ Fetch Key Financial Metrics (ALL Years, Not Just 3)
# ==========================================================
def get_key_financial_metrics(cik: str) -> dict:
    """
    Fetches the SEC 'Company Facts' JSON (XBRL data).
    Returns a simplified dictionary of key metrics:
    - Revenue
    - Net Income
    - Assets
    - Liabilities
    - Operating Income
    
    Returns ALL available fiscal years (not only 3).
    """

    cik = normalize_cik(cik)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    output = {"status": "success", "data": {}}

    try:
        r = requests.get(url, headers=SEC_HEADERS)
        if r.status_code != 200:
            return {"status": "error", "message": f"SEC API Error: {r.status_code}"}

        raw_data = r.json()
        us_gaap = raw_data.get("facts", {}).get("us-gaap", {})

        # Tags to extract
        concepts = {
            "Revenues": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"],
            "NetIncome": ["NetIncomeLoss"],
            "Assets": ["Assets"],
            "Liabilities": ["Liabilities"],
            "OperatingIncome": ["OperatingIncomeLoss"]
        }

        for label, tag_options in concepts.items():
            found = False

            for tag in tag_options:
                if tag in us_gaap:

                    units_dict = us_gaap[tag]["units"]
                    unit_key = list(units_dict.keys())[0]  # e.g. "USD"

                    df = pd.DataFrame(units_dict[unit_key])

                    # Keep annual (10-K) filings only
                    if "form" in df.columns:
                        df = df[df["form"] == "10-K"]

                    # Sort newest → oldest and dedupe by fiscal year
                    df = (
                        df.sort_values("end", ascending=False)
                          .drop_duplicates(subset=['fy'])  # KEEP ALL YEARS
                    )

                    # Save result
                    output["data"][label] = df[["end", "val", "fy", "form"]].to_dict(orient="records")
                    found = True
                    break

            # If tag not found, return empty list
            if not found:
                output["data"][label] = []

    except Exception as e:
        return {"status": "error", "message": str(e)}

    return output


# ==========================================================
# ⭐ Comparison Helper (used by /compare_kpis)
# ==========================================================
def get_company_kpis_for_compare(cik: str) -> dict:
    """
    Returns full historical revenue & net income series for comparison charts.

    Output:
    {
        "cik": "...",
        "years": [...],
        "revenue": [...],
        "net_income": [...]
    }
    """

    data = get_key_financial_metrics(cik)

    out = {"cik": cik, "years": [], "revenue": [], "net_income": []}

    if data["status"] != "success":
        return out

    rev_list = data["data"].get("Revenues", [])
    ni_list = data["data"].get("NetIncome", [])

    # Sort chronologically (oldest → newest)
    rev_list = sorted(rev_list, key=lambda x: x["fy"])
    ni_list = sorted(ni_list, key=lambda x: x["fy"])

    # Extract aligned values
    out["years"] = [item["fy"] for item in rev_list]
    out["revenue"] = [item["val"] for item in rev_list]

    # Fill missing years in Net Income if needed
    ni_by_year = {item["fy"]: item["val"] for item in ni_list}
    out["net_income"] = [ni_by_year.get(fy, None) for fy in out["years"]]

    return out
