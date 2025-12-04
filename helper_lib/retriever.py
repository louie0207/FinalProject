# helper_lib/retriever.py

from pathlib import Path
import faiss
import numpy as np
import pandas as pd
from openai import OpenAI
from .utils import INDEX_DIR, normalize_cik

client = OpenAI()

# -----------------------------
# Embeddings
# -----------------------------
def embed_texts(texts: list) -> np.ndarray:
    if not texts:
        return np.zeros((0, 1536), dtype="float32")
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    vectors = [d.embedding for d in resp.data]
    return np.array(vectors).astype("float32")

# -----------------------------
# ORIGINAL FUNCTIONS (UNTOUCHED)
# -----------------------------
def build_index_for_chunks(chunks_df: pd.DataFrame, cik: str, form: str):
    cik = normalize_cik(cik)
    texts = chunks_df["text"].tolist()
    embeddings = embed_texts(texts)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_DIR / f"{cik}_{form}.index"))
    chunks_df.to_parquet(INDEX_DIR / f"{cik}_{form}_meta.parquet")

def search(query: str, cik: str, form: str, k: int = 5) -> pd.DataFrame:
    cik = normalize_cik(cik)

    idx_path = INDEX_DIR / f"{cik}_{form}.index"
    meta_path = INDEX_DIR / f"{cik}_{form}_meta.parquet"

    if not idx_path.exists():
        return pd.DataFrame()

    index = faiss.read_index(str(idx_path))
    meta_df = pd.read_parquet(meta_path)

    q_vec = embed_texts([query])
    D, I = index.search(q_vec, k)

    valid_indices = I[0][I[0] >= 0]
    return meta_df.iloc[valid_indices].copy()


# -----------------------------
# NEW FUNCTION — Multi-Company Search
# -----------------------------
def multi_search(query: str, cik_list: list, form="10-K", k=5) -> pd.DataFrame:
    """Search across multiple companies and merge results."""
    q_vec = embed_texts([query])
    results = []

    for cik in cik_list:
        cik_norm = normalize_cik(cik)
        idx = INDEX_DIR / f"{cik_norm}_{form}.index"
        meta = INDEX_DIR / f"{cik_norm}_{form}_meta.parquet"

        if not idx.exists():
            continue

        index = faiss.read_index(str(idx))
        meta_df = pd.read_parquet(meta)

        D, I = index.search(q_vec, k)

        for dist, idx in zip(D[0], I[0]):
            if idx >= 0:
                row = meta_df.iloc[idx].copy()
                row["distance"] = float(dist)
                results.append(row)

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df.sort_values("distance").head(k)

    return df
