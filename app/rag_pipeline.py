# app/rag_pipeline.py

import json
from typing import List, Generator
from openai import OpenAI
import pandas as pd

from helper_lib.edgar_parser import build_chunks_for_filings
from helper_lib.retriever import (
    build_index_for_chunks,
    search,
    multi_search
)
from helper_lib.utils import save_chunks_df, normalize_cik
from helper_lib.xbrl import get_key_financial_metrics

client = OpenAI()

# SYSTEM PROMPT stays unchanged
SYSTEM_PROMPT_TEMPLATE = """
You are an expert financial analyst assistant (EDGAR Copilot).

### DATA SOURCES
1. **XBRL Financials**: Trusted, structured numbers.
2. **Text Context**: Excerpts from 10-K/10-Q filings.

### INSTRUCTIONS
- Prioritize XBRL financials for numbers.
- Use TEXT CONTEXT for narrative.
- Use Markdown citations EXACTLY as provided.
- Use Markdown tables when helpful.
- If something is missing, say so.

### XBRL FINANCIALS (JSON):
{xbrl_json}
"""

# -----------------------------
# Single-company ingest
# -----------------------------
def ingest_company(cik: str, form: str = "10-K", limit_per_form: int = 3):
    cik = normalize_cik(cik)
    chunks_df = build_chunks_for_filings(
        cik=cik,
        form_types=(form,),
        limit_per_form=limit_per_form
    )
    save_chunks_df(chunks_df, cik, form)
    build_index_for_chunks(chunks_df, cik, form)

# -----------------------------
# Multi-company ingest
# -----------------------------
def ingest_multiple_companies(cik_list: List[str], form="10-K", limit_per_form=3):
    for cik in cik_list:
        ingest_company(cik, form=form, limit_per_form=limit_per_form)

# -----------------------------
# Format context
# -----------------------------
def format_rag_context(hits) -> str:
    blocks = []
    for _, row in hits.iterrows():
        try:
            acc_clean = str(row['accession']).replace("-", "")
            primary_doc = row.get('primary_doc', '')
            filing_date = row.get('filing_date', 'Unknown')
            
            if primary_doc and not pd.isna(primary_doc):
                url = (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{row['cik']}/{acc_clean}/{primary_doc}"
                )
                meta = f"[Source: {row['accession']}]({url}) | Date: {filing_date}"
            else:
                meta = f"[Source: {row['accession']}] | Date: {filing_date}"

        except:
            meta = f"[Source: {row['accession']}]"

        blocks.append(f"{meta}\n{row['text']}")

    return "\n\n---\n\n".join(blocks)

# -----------------------------
# SINGLE-COMPANY CHAT
# -----------------------------
def chat_stream(cik: str, messages: List[object], form="10-K", k=5) -> Generator:
    cik = normalize_cik(cik)
    last_user_msg = messages[-1].content

    xbrl_data = get_key_financial_metrics(cik)
    xbrl_str = json.dumps(xbrl_data, indent=2)

    hits = search(last_user_msg, cik=cik, form=form, k=k)
    context_str = format_rag_context(hits)

    system_content = SYSTEM_PROMPT_TEMPLATE.format(xbrl_json=xbrl_str)
    system_content += f"\n\n### TEXT CONTEXT:\n{context_str}"

    final_messages = [{"role": "system", "content": system_content}]
    for m in messages:
        final_messages.append({"role": m.role, "content": m.content})

    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=final_messages,
        temperature=0.1,
        stream=True
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# -----------------------------
# MULTI-COMPANY CHAT
# -----------------------------
def chat_stream_multi(ciks: List[str], messages: List[object], form="10-K", k=5) -> Generator:
    last_user_msg = messages[-1].content

    # ---- Merge XBRL JSON ----
    xbrl_map = {}
    for cik in ciks:
        data = get_key_financial_metrics(cik)
        xbrl_map[cik] = data

    xbrl_str = json.dumps(xbrl_map, indent=2)

    # ---- MULTI SEARCH ----
    hits = multi_search(last_user_msg, cik_list=ciks, form=form, k=k)
    context_str = format_rag_context(hits)

    system_content = SYSTEM_PROMPT_TEMPLATE.format(xbrl_json=xbrl_str)
    system_content += "\n\n### MULTI-COMPANY TEXT CONTEXT:\n" + context_str

    final_messages = [{"role": "system", "content": system_content}]
    for m in messages:
        final_messages.append({"role": m.role, "content": m.content})

    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=final_messages,
        temperature=0.1,
        stream=True
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
