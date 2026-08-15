from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .analyzer import analyze
from .contract import Contract, infer_contract, validate_contract
from .profiles import scene_score
from .style import style_similarity
from .academic import assess_academic_target

WEIGHTS = {"faithfulness": 25, "scene_fit": 20, "naturalness": 20, "density": 15, "style_match": 10, "readability": 5, "pattern_risk": 5}
LABELS = {"faithfulness": "事实保真", "scene_fit": "场景适配", "naturalness": "自然度", "density": "信息密度", "style_match": "文风匹配", "readability": "可读性", "pattern_risk": "模式风险"}


@dataclass
class Score:
    status: str
    total: float
    dimensions: dict
    failures: list
    warnings: list
    evidence: dict
    dimension_details: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def score(candidate: str, source: str | None = None, scene: str = "general", contract: Contract | None = None, style_profile: dict | None = None) -> Score:
    source = source or ""
    contract = contract or infer_contract(source)
    validation = validate_contract(source, candidate, contract)
    report = analyze(candidate)
    scene_value, scene_misses = scene_score(candidate, scene)
    risk_count = len([f for f in report["findings"] if f["severity"] == "WARN"])
    natural = max(1.0, 5.0 - min(3.5, risk_count * 0.4))
    density = _density(candidate)
    readability = _readability(report)
    style_value = style_similarity(candidate, style_profile)
    pattern_value = max(1.0, 5.0 - min(4.0, risk_count * 0.55))
    faith = 5.0 if validation["passed"] else max(0.0, 5.0 - len(validation["failures"]) * 2)
    dims = {"faithfulness": faith, "scene_fit": scene_value, "naturalness": natural, "density": density, "style_match": style_value, "readability": readability, "pattern_risk": pattern_value}
    total = round(sum(dims[k] * WEIGHTS[k] / 5 for k in WEIGHTS), 1)
    failures = validation["failures"]
    warnings = validation["warnings"] + [{"tag": "scene.fit", "message": m} for m in scene_misses]
    academic_assessment = assess_academic_target(contract.metadata) if scene == "academic" else None
    details = _dimension_details(dims, validation, report, scene_misses, style_profile)
    if academic_assessment:
        details["scene_fit"]["evidence"] = {"scene_misses": scene_misses, "academic_target": academic_assessment}
        details["scene_fit"]["deductions"] += academic_assessment["missing"] + academic_assessment["warnings"]
        details["scene_fit"]["improve"] += " 补齐目标期刊、文章类型、作者指南及带年份的收录和分区信息。"
    return Score("reject" if failures else "pass" if total >= 82 and not scene_misses else "review", total, {k: round(v, 2) for k, v in dims.items()}, failures, warnings, {"analysis": report, "scene_misses": scene_misses, "contract": contract.to_dict(), "academic_target": academic_assessment}, details)


def _dimension_details(dims, validation, report, scene_misses, style_profile):
    findings = report.get("findings", [])
    risk_evidence = [{"line": x.get("line"), "quote": x.get("evidence"), "tag": x.get("tag")} for x in findings]
    reasons = {
        "faithfulness": {
            "positive": ["LOCK、数字、链接和结构均通过内容契约检查"] if validation["passed"] else [],
            "deductions": validation["failures"] + validation["warnings"],
            "evidence": validation,
            "improve": "恢复遗漏或被改变的事实、限定语、数字、链接和结构；无法核实时标记待确认。",
        },
        "scene_fit": {
            "positive": ["未发现静态场景必备项缺失"] if not scene_misses else [],
            "deductions": scene_misses,
            "evidence": scene_misses,
            "improve": "补足目标读者在当前渠道完成任务所需的信息、结构、下一步和边界。",
        },
        "naturalness": {
            "positive": ["未命中明显模板化表达"] if not findings else [],
            "deductions": [x.get("message") for x in findings if x.get("severity") == "WARN"],
            "evidence": risk_evidence,
            "improve": "只修改有上下文证据的机械、空泛或表演性表达；常见但有功能的礼貌语不自动删除。",
        },
        "density": {
            "positive": ["段落具有基本信息承载能力"] if dims["density"] >= 4 else [],
            "deductions": ["存在空泛动作、同义复述或段落推进不足"] if dims["density"] < 4 else [],
            "evidence": risk_evidence,
            "improve": "用材料中可确认的主体、动作、条件和结果替代空泛概念；删除不推进任务的重复。",
        },
        "style_match": {
            "positive": ["已依据用户样文比较可观察风格"] if style_profile else ["未提供样文，按场景默认语体评估"],
            "deductions": [] if dims["style_match"] >= 4 else ["与样文或场景默认语体仍有差距"],
            "evidence": style_profile or {"basis": "scene_default"},
            "improve": "匹配句长、段长、称呼、语气和结尾习惯，不复制样文独特措辞。",
        },
        "readability": {
            "positive": [f"平均句长为 {report.get('sentence_length', {}).get('mean', 0)} 字"],
            "deductions": [] if dims["readability"] >= 4 else ["句子负担或切分方式影响理解"],
            "evidence": report.get("sentence_length", {}),
            "improve": "优先拆解承载多个动作或条件的句子，保留必要的因果和限定关系。",
        },
        "pattern_risk": {
            "positive": ["未发现需要复核的高频写作模式"] if not findings else [],
            "deductions": [x.get("tag") for x in findings],
            "evidence": risk_evidence,
            "improve": "模式命中仅用于定位；结合上下文确认无信息价值后再改，不以降低检测器分数为目标。",
        },
    }
    return {key: {"label": LABELS[key], "score_5": round(dims[key], 2), "weight": WEIGHTS[key], "weighted_score": round(dims[key] * WEIGHTS[key] / 5, 1), **reasons[key]} for key in WEIGHTS}


def _density(text: str) -> float:
    if not text.strip():
        return 0.0
    vague = len(re.findall(r"赋能|助力|打造|推动|意义重大|至关重要|全方位", text))
    repeats = len(re.findall(r"换句话说|也就是说|总而言之", text))
    return round(max(1.0, 4.6 - vague * 0.3 - repeats * 0.25), 2)


def _readability(report: dict) -> float:
    mean = report["sentence_length"]["mean"]
    if mean == 0:
        return 0.0
    if 8 <= mean <= 42:
        return 4.6
    if 5 <= mean <= 55:
        return 3.8
    return 2.8
