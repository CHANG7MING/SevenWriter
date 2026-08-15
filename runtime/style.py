from __future__ import annotations

import re
from collections import Counter


CONNECTORS = ("但是", "不过", "所以", "因此", "同时", "另外", "其实", "比如", "例如", "换句话说")


def extract_style(texts: list[str]) -> dict:
    text = "\n\n".join(t for t in texts if t.strip())
    sentences = [s.strip() for s in re.split(r"[。！？!?]+", text) if s.strip()]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    lengths = [len(s) for s in sentences]
    para_lengths = [len(p) for p in paragraphs]
    punctuation = Counter(ch for ch in text if ch in "，。！？：；、…—,.!?:;")
    connectors = {c: text.count(c) for c in CONNECTORS if text.count(c)}
    first_person = len(re.findall(r"我|我们|本人", text)) / max(1, len(sentences))
    questions = len(re.findall(r"[？?]", text)) / max(1, len(sentences))
    return {
        "samples": len(texts),
        "characters": len(text),
        "sentence_length": _summary(lengths),
        "paragraph_length": _summary(para_lengths),
        "punctuation": dict(punctuation.most_common()),
        "connectors": connectors,
        "first_person_per_sentence": round(first_person, 3),
        "question_ratio": round(questions, 3),
        "ending_patterns": _endings(paragraphs),
        "confidence": "high" if len(text) >= 3000 else "medium" if len(text) >= 800 else "low",
        "notice": "仅描述可观察特征，不复制独特措辞，也不推断作者身份。",
    }


def style_similarity(candidate: str, profile: dict | None) -> float:
    if not profile or profile.get("confidence") == "low":
        return 3.0
    current = extract_style([candidate])
    target = profile["sentence_length"]["mean"]
    actual = current["sentence_length"]["mean"]
    if not target or not actual:
        return 2.5
    ratio = abs(actual - target) / max(1, target)
    return round(max(1.0, 5.0 - ratio * 4), 2)


def _summary(values: list[int]) -> dict:
    if not values:
        return {"min": 0, "max": 0, "mean": 0.0, "median": 0.0}
    ordered = sorted(values)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    return {"min": min(values), "max": max(values), "mean": round(sum(values) / len(values), 2), "median": round(median, 2)}


def _endings(paragraphs: list[str]) -> dict:
    endings = Counter(p[-1] for p in paragraphs if p)
    return dict(endings.most_common())
