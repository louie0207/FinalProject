# app/main.py
import json
from typing import List, Optional
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from .rag_pipeline import ingest_company, chat_stream
from helper_lib.xbrl import get_key_financial_metrics

app = FastAPI(
    title="EDGAR Analyst Copilot",
    version="0.2.0",
    description="Financial RAG with XBRL Grounding and Streaming Chat."
)

class Message(BaseModel):
    role: str
    content: str

class IngestRequest(BaseModel):
    cik: str
    form: str = "10-K"
    limit_per_form: int = 3

class ChatRequest(BaseModel):
    cik: str
    messages: List[Message]
    form: str = "10-K"
    k: int = 5

@app.get("/")
def root():
    return {"status": "ok", "message": "EDGAR Copilot (Streaming + XBRL) Ready"}

@app.post("/ingest")
def ingest(req: IngestRequest):
    """Downloads filings, chunks them, and builds the Vector Index."""
    ingest_company(cik=req.cik, form=req.form, limit_per_form=req.limit_per_form)
    return {"status": "ok", "message": f"Ingested {req.form} for CIK={req.cik}"}

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Streams the LLM response. 
    It automatically fetches XBRL data and RAG context before answering.
    """
    return StreamingResponse(
        chat_stream(
            cik=req.cik,
            messages=req.messages,
            form=req.form,
            k=req.k
        ),
        media_type="text/event-stream"
    )

@app.get("/kpi/{cik}")
def get_kpis(cik: str):
    """
    Returns raw structured XBRL data for frontend tables (Table-Grounded).
    """
    data = get_key_financial_metrics(cik)
    return {"cik": cik, "kpis": data}