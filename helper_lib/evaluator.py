# helper_lib/evaluator.py

"""
Very lightweight evaluation helpers.

These are not rigorous metrics, but they give quick diagnostics like:
- whether numeric tokens in the answer are present in the context
- rough length / coverage stats
"""

import re
from typing import List, Dict


NUMERIC_PATTERN = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def extract_numbers(text: str) -> List[str]:
    """
    Extract normalized numeric strings from text.
    """
    nums = NUMERIC_PATTERN.findall(text)
    # normalize: remove commas
    nums = [n.replace(",", "") for n in nums]
    return nums


def numeric_consistency_score(answer: str, context: str) -> float:
    """
    Fraction of numeric values in answer that also appear in context.
    Returns a score in [0, 1]. If no numbers in answer, returns 1.0.
    """
    ans_nums = extract_numbers(answer)
    if not ans_nums:
        return 1.0

    ctx_nums = set(extract_numbers(context))
    if not ctx_nums:
        return 0.0

    matches = sum(1 for n in ans_nums if n in ctx_nums)
    return matches / len(ans_nums)


def build_context_from_rows(rows) -> str:
    """
    Concatenate text fields from retrieved chunks into a single string
    for evaluation.
    """
    blocks = []
    for _, row in rows.iterrows():
        blocks.append(row["text"])
    return "\n\n".join(blocks)


def evaluate_qa(
    answer: str,
    retrieved_rows,
) -> Dict[str, float]:
    """
    Simple evaluation summary for a single Q/A pair.
    """
    context = build_context_from_rows(retrieved_rows)
    num_score = numeric_consistency_score(answer, context)
    return {
        "numeric_consistency": num_score,
        "answer_length_chars": float(len(answer)),
        "num_retrieved_chunks": float(len(retrieved_rows)),
    }
