# app/rag_pipeline.py
import json
from typing import List, Generator, Dict
from openai import OpenAI
from helper_lib.edgar_parser import build_chunks_for_filings
from helper_lib.retriever import build_index_for_chunks, search
from helper_lib.utils import save_chunks_df, normalize_cik
from helper_lib.xbrl import get_key_financial_metrics

client = OpenAI()

SYSTEM_PROMPT_TEMPLATE = """
You are an expert financial analyst assistant (EDGAR Copilot).

### DATA SOURCES
1. **XBRL Financials**: Trusted, structured numbers for this company.
2. **Text Context**: Excerpts from 10-K/10-Q filings.

### INSTRUCTIONS
- **Grounding**: prioritizing the 'XBRL Financials' for specific numbers (Revenue, Net Income). Use 'Text Context' for explanations, risks, and qualitative analysis.
- **Citations**: You MUST cite the 'Text Context' using [Source: AccessionNumber].
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
        meta = f"[Source: {row['accession']} | Date: {row['filing_date']} | Section: {row.get('primary_doc','')}]"
        blocks.append(f"{meta}\n{row['text']}")
    return "\n\n---\n\n".join(blocks)

def chat_stream(cik: str, messages: List[object], form: str = "10-K", k: int = 5) -> Generator:
    cik = normalize_cik(cik)
    
    # 1. Get latest query
    # Note: messages is a list of Pydantic models, so use .content or dict access
    last_user_msg = messages[-1].content
    
    # 2. Parallel Data Fetching
    # A. Get XBRL Data (The "Table-Grounded" Truth)
    xbrl_data = get_key_financial_metrics(cik)
    xbrl_str = json.dumps(xbrl_data, indent=2)
    
    # B. Get RAG Context (The "Finance-Aware Retrieval")
    hits = search(last_user_msg, cik=cik, form=form, k=k)
    context_str = format_rag_context(hits)
    
    # 3. Build System Prompt
    system_content = SYSTEM_PROMPT_TEMPLATE.format(xbrl_json=xbrl_str)
    system_content += f"\n\n### TEXT CONTEXT:\n{context_str}"
    
    # 4. Prepare Message History
    # We prepend the system prompt to the user's history
    final_messages = [{"role": "system", "content": system_content}]
    for m in messages:
        final_messages.append({"role": m.role, "content": m.content})
    
    # 5. Stream from OpenAI
    stream = client.chat.completions.create(
        model="gpt-4o", # Recommended for complex reasoning
        messages=final_messages,
        temperature=0.1,
        stream=True
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content