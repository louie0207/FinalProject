# helper_lib/xbrl.py
import requests
import pandas as pd
from .utils import SEC_HEADERS, normalize_cik

def get_key_financial_metrics(cik: str) -> dict:
    """
    Fetches the 'Company Facts' JSON from SEC (XBRL data).
    Returns a simplified dictionary of key metrics (Revenue, Net Income, Assets).
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
        
        # Define concepts to extract
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
                    # Get the units (usually USD)
                    units_dict = us_gaap[tag]["units"]
                    unit_key = list(units_dict.keys())[0] # e.g. "USD"
                    
                    # Create DataFrame to sort by date
                    df = pd.DataFrame(units_dict[unit_key])
                    
                    # Filter: 10-K only, recent years
                    if "form" in df.columns:
                        df = df[df["form"] == "10-K"]
                        
                    df = df.sort_values("end", ascending=False).drop_duplicates(subset=['fy']).head(3)
                    
                    # Store as list of dicts
                    output["data"][label] = df[["end", "val", "fy", "form"]].to_dict(orient="records")
                    found = True
                    break # Stop if we found the primary tag
            
            if not found:
                output["data"][label] = []

    except Exception as e:
        return {"status": "error", "message": str(e)}
        
    return output