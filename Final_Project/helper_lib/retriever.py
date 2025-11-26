# helper_lib/retriever.py
from pathlib import Path
import faiss
import numpy as np
import pandas as pd
from openai import OpenAI
from .utils import INDEX_DIR, normalize_cik

client = OpenAI()

def embed_texts(texts: list) -> np.ndarray:
    if not texts:
        return np.zeros((0, 1536), dtype="float32")
    # Using small for speed/cost, large for accuracy. 
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    vectors = [d.embedding for d in resp.data]
    return np.array(vectors).astype("float32")

def build_index_for_chunks(chunks_df: pd.DataFrame, cik: str, form: str):
    cik = normalize_cik(cik)
    texts = chunks_df["text"].tolist()
    embeddings = embed_texts(texts)
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # Save Index and Metadata
    faiss.write_index(index, str(INDEX_DIR / f"{cik}_{form}.index"))
    chunks_df.to_parquet(INDEX_DIR / f"{cik}_{form}_meta.parquet")

def search(query: str, cik: str, form: str, k: int = 5) -> pd.DataFrame:
    cik = normalize_cik(cik)
    idx_path = INDEX_DIR / f"{cik}_{form}.index"
    meta_path = INDEX_DIR / f"{cik}_{form}_meta.parquet"
    
    if not idx_path.exists():
        # Fallback or empty return
        return pd.DataFrame()

    index = faiss.read_index(str(idx_path))
    meta_df = pd.read_parquet(meta_path)
    
    q_vec = embed_texts([query])
    D, I = index.search(q_vec, k)
    
    # Filter invalid indices
    valid_indices = I[0][I[0] >= 0]
    return meta_df.iloc[valid_indices].copy()