# EDGAR Analyst Copilot

RAG pipeline over SEC EDGAR filings (10-K / 10-Q) with:
- SEC API ingestion (submissions + filings)
- HTML → text cleaning and chunking
- OpenAI embeddings + FAISS vector store
- FastAPI API for ingest + question answering

> **Important:** You must set:
> - `SEC_USER_AGENT` (email or app identifier for SEC)
> - `OPENAI_API_KEY` (for embeddings + chat)

---

## Setup (local, with uv or pip)

```bash
cd EDGAR_Analyst_Copilot

# with uv
uv venv
source .venv/bin/activate
uv pip install -e .

# or with pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
