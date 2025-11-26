import json
from typing import List, Generator
from openai import OpenAI
from helper_lib.edgar_parser import build_chunks_for_filings
from helper_lib.retriever import build_index_for_chunks, search
from helper_lib.utils import save_chunks_df, normalize_cik
from helper_lib.xbrl import get_key_financial_metrics
import pandas as pd

client = OpenAI()

# --- UPDATED PROMPT: Explicitly asks for Markdown Links ---
SYSTEM_PROMPT_TEMPLATE = """
You are an expert financial analyst assistant (EDGAR Copilot).

### DATA SOURCES
1. **XBRL Financials**: Trusted, structured numbers for this company.
2. **Text Context**: Excerpts from 10-K/10-Q filings.

### INSTRUCTIONS
- **Grounding**: Prioritize 'XBRL Financials' for specific numbers. Use 'Text Context' for explanations and risks.
- **Citations**: When citing the 'Text Context', you MUST use the exact Markdown link format provided in the context header (e.g., `[Source: 000...](https://...)`). Do NOT strip the URL.
- **Tables**: If asked for a summary, format it as a Markdown table.
- **Honesty**: If the data isn't there, say "Not found in source."

### XBRL FINANCIALS (JSON):
{xbrl_json}
"""

def ingest_company(cik: str, form: str = "10-K", limit_per_form: int = 3):
    cik = normalize_cik(cik)
    chunks_df = build_chunks_for_filings(cik=cik, form_types=(form,), limit_per_form=limit_per_form)
    save_chunks_df(chunks_df, cik, form)
    build_index_for_chunks(chunks_df, cik, form)

def format_rag_context(hits) -> str:
    blocks = []
    for _, row in hits.iterrows():
        try:
            acc_clean = str(row['accession']).replace("-", "")
            primary_doc = row.get('primary_doc', '')
            filing_date = row.get('filing_date', 'Unknown Date')
            
            if primary_doc and not pd.isna(primary_doc):
                # Construct SEC URL
                url = f"https://www.sec.gov/Archives/edgar/data/{row['cik']}/{acc_clean}/{primary_doc}"
                # Standard Markdown Link Format: [Text](URL)
                meta = f"[Source: {row['accession']}]({url}) | Date: {filing_date}"
            else:
                meta = f"[Source: {row['accession']}] | Date: {filing_date}"
                
        except Exception as e:
            print(f"⚠️ Link Generation Error: {e}")
            meta = f"[Source: {row['accession']}]"
            
        blocks.append(f"{meta}\n{row['text']}")
    return "\n\n---\n\n".join(blocks)

def chat_stream(cik: str, messages: List[object], form: str = "10-K", k: int = 5) -> Generator:
    cik = normalize_cik(cik)
    last_user_msg = messages[-1].content
    
    # Fetch Data
    xbrl_data = get_key_financial_metrics(cik)
    xbrl_str = json.dumps(xbrl_data, indent=2)
    
    hits = search(last_user_msg, cik=cik, form=form, k=k)
    context_str = format_rag_context(hits)
    
    # Build Prompt
    system_content = SYSTEM_PROMPT_TEMPLATE.format(xbrl_json=xbrl_str)
    system_content += f"\n\n### TEXT CONTEXT:\n{context_str}"
    
    final_messages = [{"role": "system", "content": system_content}]
    for m in messages:
        final_messages.append({"role": m.role, "content": m.content})
    
    # Stream Response
    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=final_messages,
        temperature=0.1,
        stream=True
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content