# core/dedup.py
from __future__ import annotations
from difflib import SequenceMatcher


def deduplicate_findings(findings: list, threshold: float = 0.80) -> list:
    """
    Remove near-duplicate findings using sequence matching on content[:400].
    When two findings are duplicates, keep the one with the higher confidence_score.
    """
    if len(findings) <= 1:
        return findings

    kept: list[dict] = []
    for candidate in findings:
        c_text = candidate.get("content", "").lower()[:400]
        dup_idx = None
        for i, retained in enumerate(kept):
            r_text = retained.get("content", "").lower()[:400]
            if SequenceMatcher(None, c_text, r_text).ratio() > threshold:
                dup_idx = i
                break

        if dup_idx is None:
            kept.append(candidate)
        elif candidate.get("confidence_score", 0) > kept[dup_idx].get("confidence_score", 0):
            kept[dup_idx] = candidate

    removed = len(findings) - len(kept)
    if removed:
        print(f"[Dedup] Removed {removed} near-duplicates — {len(kept)} unique findings kept")
    return kept
