from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

URL_RE = re.compile(r"https?://[^\s)\]>]+")
NUMBER_RE = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?:%|％|万|亿|元|年|月|日|小时|分钟)?(?![\w])")
DATE_RE = re.compile(r"(?:\d{4}[年/-])?\d{1,2}[月/-]\d{1,2}日?|(?:今天|明天|后天|本周|下周)(?:上午|下午|晚上)?")
MODAL_RE = re.compile(r"可能|预计|计划|建议|应当|必须|已经|尚未|不保证|不得")
UNCERTAIN_RE = re.compile(r"可能|预计|计划|拟|暂定|尚未|不保证|有望|视.{0,8}而定")
CERTAINTY_RE = re.compile(r"一定|肯定|保证|确保|必然|百分之百|绝对|务必|处理完成|已经完成")
MARKDOWN_RE = re.compile(r"^(#{1,6}\s+|```|>|\s*[-*+]\s+|\|)", re.M)


@dataclass
class Contract:
    locks: list[str] = field(default_factory=list)
    soft_locks: list[str] = field(default_factory=list)
    preserve: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    max_length_delta: float = 0.15
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def infer_contract(text: str, explicit: dict | None = None) -> Contract:
    explicit = explicit or {}
    locks = list(explicit.get("locks", []))
    for value in URL_RE.findall(text) + NUMBER_RE.findall(text) + DATE_RE.findall(text):
        if value and value not in locks:
            locks.append(value)
    preserve = list(explicit.get("preserve", []))
    if MARKDOWN_RE.search(text):
        preserve.extend(x for x in ("markdown_structure", "code_fences", "urls") if x not in preserve)
    return Contract(
        locks=locks,
        soft_locks=list(explicit.get("soft_locks", [])),
        preserve=preserve,
        unknowns=list(explicit.get("unknowns", [])),
        max_length_delta=float(explicit.get("max_length_delta", 0.15)),
        metadata=dict(explicit.get("metadata", {})),
    )


def validate_contract(source: str, candidate: str, contract: Contract) -> dict:
    failures, warnings = [], []
    for item in contract.locks:
        if item not in candidate:
            failures.append({"tag": "faithfulness.lock", "value": item})
    for item in contract.soft_locks:
        if item not in candidate:
            warnings.append({"tag": "faithfulness.soft_lock", "value": item})
    source_modals, candidate_modals = set(MODAL_RE.findall(source)), set(MODAL_RE.findall(candidate))
    if source_modals != candidate_modals:
        warnings.append({"tag": "faithfulness.modality", "source": sorted(source_modals), "candidate": sorted(candidate_modals)})
    if UNCERTAIN_RE.search(source) and not UNCERTAIN_RE.search(candidate) and CERTAINTY_RE.search(candidate):
        failures.append({"tag": "faithfulness.modality_upgrade", "source": UNCERTAIN_RE.findall(source), "candidate": CERTAINTY_RE.findall(candidate), "message": "把预计、可能或计划升级成了确定承诺"})
    if "markdown_structure" in contract.preserve:
        src = markdown_signature(source)
        dst = markdown_signature(candidate)
        if src != dst:
            failures.append({"tag": "document.structure", "source": src, "candidate": dst})
    if source:
        delta = abs(len(candidate) - len(source)) / max(1, len(source))
        if delta > contract.max_length_delta:
            warnings.append({"tag": "scene.length", "delta": round(delta, 3), "limit": contract.max_length_delta})
    return {"passed": not failures, "failures": failures, "warnings": warnings}


def markdown_signature(text: str) -> dict:
    return {
        "headings": re.findall(r"^(#{1,6})\s", text, re.M),
        "fences": len(re.findall(r"^```", text, re.M)),
        "urls": URL_RE.findall(text),
        "tables": len(re.findall(r"^\|", text, re.M)),
        "quotes": len(re.findall(r"^>", text, re.M)),
    }
