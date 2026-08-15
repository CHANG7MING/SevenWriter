from __future__ import annotations

import re
from collections import Counter

PATTERNS = {
    "template": [r"首先.{0,80}其次", r"综上所述", r"总而言之", r"在当今.{0,12}(时代|背景下)"],
    "contrast": [r"不是.{1,40}而是", r"不仅.{1,40}(更|还)", r"与其说.{1,40}不如说", r"看似.{1,40}实则"],
    "elevation": [r"真正重要的是", r"这背后(体现|反映|折射)", r"标志着.{0,30}(一步|里程碑)"],
    "vague": [r"赋能", r"助力", r"打造", r"推动", r"实现闭环", r"全方位", r"极致体验"],
    "hedging": [r"可能在一定程度上", r"或许可能", r"相对而言.{0,12}比较"],
    "service_tone": [r"感谢您的理解与支持", r"如有任何问题请随时联系我们", r"第一时间为您处理"],
    "forced_colloquial": [r"真的绝了", r"闭眼冲", r"姐妹们", r"你知道吗[？?]?"],
}


def analyze(text: str) -> dict:
    findings = []
    for tag, patterns in PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.S | re.I):
                findings.append({"severity": "WARN", "tag": f"naturalness.{tag}", "line": text.count("\n", 0, match.start()) + 1, "evidence": match.group(0)[:100], "message": "结合上下文判断是否为空泛、机械或必要表达。"})
    sentence_lengths = [len(s.strip()) for s in re.split(r"[。！？!?\n]+", text) if s.strip()]
    repeated = [w for w, n in Counter(re.findall(r"首先|其次|最后|同时|此外|因此|然而|值得注意的是", text)).items() if n >= 3]
    symmetry = _symmetry(sentence_lengths)
    if symmetry >= 0.85 and len(sentence_lengths) >= 6:
        findings.append({"severity": "INFO", "tag": "naturalness.rhythm", "line": 1, "evidence": f"句长一致度 {symmetry}", "message": "句长高度接近；确认是否由内容自然形成。"})
    return {"characters": len(text), "paragraphs": len([p for p in text.splitlines() if p.strip()]), "sentence_length": _stats(sentence_lengths), "repeated_connectors": repeated, "findings": sorted(findings, key=lambda x: (x["line"], x["tag"])), "notice": "启发式命中不是作者身份判断，也不等于必须修改。"}


def _stats(values: list[int]) -> dict:
    if not values:
        return {"min": 0, "max": 0, "mean": 0.0, "stdev": 0.0}
    mean = sum(values) / len(values)
    stdev = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5
    return {"min": min(values), "max": max(values), "mean": round(mean, 1), "stdev": round(stdev, 1)}


def _symmetry(values: list[int]) -> float:
    if not values or sum(values) == 0:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return round(max(0.0, 1.0 - variance ** 0.5 / max(1, mean)), 2)
