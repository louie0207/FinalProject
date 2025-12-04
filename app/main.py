# app/main.py

import json
from typing import List
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .rag_pipeline import (
    ingest_company,
    ingest_multiple_companies,
    chat_stream,
    chat_stream_multi
)

from helper_lib.xbrl import (
    get_key_financial_metrics,
    get_company_kpis_for_compare
)

app = FastAPI(
    title="EDGAR Analyst Copilot",
    version="0.4.0",
    description="Financial RAG with XBRL Grounding and Multi-Company Comparison."
)

# -----------------------------
# MODELS
# -----------------------------
class Message(BaseModel):
    role: str
    content: str

class IngestRequest(BaseModel):
    cik: str
    form: str = "10-K"
    limit_per_form: int = 3

class MultiIngestRequest(BaseModel):
    ciks: List[str]
    form: str = "10-K"
    limit_per_form: int = 3

class ChatRequest(BaseModel):
    cik: str
    messages: List[Message]
    form: str = "10-K"
    k: int = 5

class MultiChatRequest(BaseModel):
    ciks: List[str]
    messages: List[Message]
    form: str = "10-K"
    k: int = 5


# -----------------------------
# ROUTES
# -----------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "EDGAR Copilot Ready"}

# SINGLE INGEST
@app.post("/ingest")
def ingest(req: IngestRequest):
    ingest_company(
        cik=req.cik,
        form=req.form,
        limit_per_form=req.limit_per_form
    )
    return {"status": "ok", "message": f"Ingested {req.form} for CIK={req.cik}"}

# MULTI-INGEST
@app.post("/ingest_all")
def ingest_all(req: MultiIngestRequest):
    ingest_multiple_companies(
        cik_list=req.ciks,
        form=req.form,
        limit_per_form=req.limit_per_form
    )
    return {"status": "ok", "message": f"Ingested {len(req.ciks)} companies"}

# SINGLE COMPANY CHAT
@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    return StreamingResponse(
        chat_stream(
            cik=req.cik,
            messages=req.messages,
            form=req.form,
            k=req.k
        ),
        media_type="text/event-stream"
    )

# MULTI-COMPANY CHAT
@app.post("/chat_multi")
async def chat_multi_endpoint(req: MultiChatRequest):
    return StreamingResponse(
        chat_stream_multi(
            ciks=req.ciks,
            messages=req.messages,
            form=req.form,
            k=req.k
        ),
        media_type="text/event-stream"
    )

# KPI (Single)
@app.get("/kpi/{cik}")
def get_kpis(cik: str):
    data = get_key_financial_metrics(cik)
    return {"cik": cik, "kpis": data}

# Comparison KPIs
@app.get("/compare_kpis")
def compare_kpis(cik1: str, cik2: str):
    data1 = get_company_kpis_for_compare(cik1)
    data2 = get_company_kpis_for_compare(cik2)
    return {"company1": data1, "company2": data2}
