# helper_lib/utils.py
import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
import tiktoken
import pandas as pd
import requests  # Added for Ticker lookup

# Paths
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw_filings"
CHUNK_DIR = DATA_DIR / "chunks"
INDEX_DIR = DATA_DIR / "indexes"

for d in [DATA_DIR, RAW_DIR, CHUNK_DIR, INDEX_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Headers
SEC_HEADERS = {
    "User-Agent": os.getenv("SEC_USER_AGENT", "academic_project@university.edu")
}

def get_cik_from_ticker(ticker: str) -> str:
    """
    Fetches the SEC's official ticker-to-CIK mapping.
    """
    try:
        print(f"🔍 Looking up CIK for ticker: {ticker}...")
        url = "https://www.sec.gov/files/company_tickers.json"
        r = requests.get(url, headers=SEC_HEADERS)
        r.raise_for_status()
        data = r.json()
        
        ticker_upper = ticker.upper().strip()
        
        # The SEC JSON structure is a dictionary of dictionaries
        for entry in data.values():
            if entry["ticker"] == ticker_upper:
                found_cik = str(entry["cik_str"])
                print(f"✅ Found CIK for {ticker}: {found_cik}")
                return found_cik
                
        raise ValueError(f"Ticker symbol '{ticker}' not found in SEC database.")
    except Exception as e:
        print(f"❌ Error looking up ticker: {e}")
        # Return the original input if lookup fails (fallback)
        return ticker

def normalize_cik(cik_input: str) -> str:
    """
    Smart Normalizer:
    - If input is 'AAPL' (Letters) -> Look up CIK -> Return '0000320193'
    - If input is '320193' (Digits) -> Return '0000320193'
    """
    cik_input = str(cik_input).strip()
    
    # Check if input contains letters (implies it's a Ticker, not a CIK)
    if not cik_input.isdigit():
        cik_input = get_cik_from_ticker(cik_input)
        
    return cik_input.zfill(10)

def clean_html_text(html_content: str) -> str:
    """
    Parses HTML to text but preserves table structures as pipe-delimited rows.
    Critical for 'Table-Grounded' RAG.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 1. Transform tables to pipe-delimited text
    for table in soup.find_all("table"):
        rows_text = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            # Filter empty rows
            if any(cells):
                rows_text.append(" | ".join(cells))
        
        # Replace the table tag with the formatted text
        table_replacement = "\n[TABLE START]\n" + "\n".join(rows_text) + "\n[TABLE END]\n"
        table.replace_with(table_replacement)
        
    # 2. Get text and clean excessive whitespace
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n\s*\n", "\n\n", text) # limit to max 2 newlines
    return text.strip()

_tokenizer = tiktoken.get_encoding("cl100k_base")

def chunk_text(text: str, max_tokens: int = 1000, overlap: int = 200) -> list:
    tokens = _tokenizer.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunks.append(_tokenizer.decode(chunk_tokens))
        start += max_tokens - overlap
    return chunks

def save_chunks_df(df: pd.DataFrame, cik: str, form: str):
    path = CHUNK_DIR / f"chunks_{normalize_cik(cik)}_{form}.parquet"
    df.to_parquet(path, index=False)