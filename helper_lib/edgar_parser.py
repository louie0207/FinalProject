# helper_lib/edgar_parser.py
from pathlib import Path
import requests
import pandas as pd
from .utils import SEC_HEADERS, RAW_DIR, normalize_cik, clean_html_text, chunk_text

def get_company_filings(cik: str) -> pd.DataFrame:
    cik = normalize_cik(cik)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(url, headers=SEC_HEADERS)
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data["filings"]["recent"])

def build_chunks_for_filings(cik: str, form_types=("10-K",), limit_per_form=3) -> pd.DataFrame:
    cik = normalize_cik(cik)
    df = get_company_filings(cik)
    
    # Filter forms
    df = df[df["form"].isin(form_types)].head(limit_per_form)
    
    all_chunks = []
    
    for _, row in df.iterrows():
        acc = row["accessionNumber"].replace("-", "")
        doc = row["primaryDocument"]
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
        
        # Download
        save_path = RAW_DIR / f"{acc}.html"
        if not save_path.exists():
            resp = requests.get(url, headers=SEC_HEADERS)
            save_path.write_text(resp.text, encoding="utf-8", errors="ignore")
            
        # Parse & Chunk
        raw_text = save_path.read_text(encoding="utf-8", errors="ignore")
        clean_text = clean_html_text(raw_text)
        chunks = chunk_text(clean_text)
        
        for i, txt in enumerate(chunks):
            all_chunks.append({
                "chunk_id": f"{row['accessionNumber']}_{i}",
                "cik": cik,
                "accession": row["accessionNumber"],
                "filing_date": row["filingDate"],
                "primary_doc": row["primaryDocument"], # <--- Ensures filenames are saved for links
                "text": txt
            })
            
    return pd.DataFrame(all_chunks)