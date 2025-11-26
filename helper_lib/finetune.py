# helper_lib/finetune.py

"""
Simple utilities to log Q/A pairs and prepare an OpenAI finetune-style dataset.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from .utils import QA_LOG_DIR, normalize_cik


def _qa_log_path(cik: str, form: str) -> Path:
    cik = normalize_cik(cik)
    return QA_LOG_DIR / f"qa_{cik}_{form}.jsonl"


def log_qa_example(
    cik: str,
    form: str,
    question: str,
    answer: str,
    sources: List[Dict[str, Any]],
) -> Path:
    """
    Append a Q/A example to a JSONL log file.
    """
    path = _qa_log_path(cik, form)
    record = {
        "cik": normalize_cik(cik),
        "form": form,
        "question": question,
        "answer": answer,
        "sources": sources,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return path


def build_openai_finetune_dataset(
    cik: str,
    form: str,
    system_prompt: str,
) -> Path:
    """
    Convert the QA log to an OpenAI finetune-style JSONL dataset
    with chat 'messages'.
    """
    log_path = _qa_log_path(cik, form)
    if not log_path.exists():
        raise FileNotFoundError(
            f"No QA log found for CIK={cik}, form={form}: {log_path}"
        )

    out_path = QA_LOG_DIR / f"openai_finetune_{normalize_cik(cik)}_{form}.jsonl"

    with log_path.open("r", encoding="utf-8") as fin, \
            out_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            record = json.loads(line)
            question = record["question"]
            answer = record["answer"]

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ]

            fout.write(json.dumps({"messages": messages}) + "\n")

    return out_path
