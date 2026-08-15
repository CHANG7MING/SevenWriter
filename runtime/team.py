from __future__ import annotations

import json
import re

from .jury import select_panel

ROLE_MAP = {"fidelity": "evidence", "scene": "writer", "expression": "final_review"}
ROLE_LABELS = {"evidence": "资料校核席", "writer": "场景主笔席", "final_review": "独立终审席"}
TEAM_WEIGHTS = {"evidence": 0.30, "writer": 0.20, "final_review": 0.50}


def select_editorial_team(scene: str, seed: int | None = None) -> dict:
    panel = select_panel(scene, seed)
    members = []
    for member in panel["members"]:
        item = dict(member)
        item["role"] = ROLE_MAP[item.pop("function")]
        item["role_label"] = ROLE_LABELS[item["role"]]
        members.append(item)
    return {"seed": panel["seed"], "scene": scene, "members": members, "workflow": ["evidence", "writer", "final_review"]}


def run_editorial_team(generator, source: str, task: str, scene: str, contract: dict, seed: int | None = None) -> dict:
    team = select_editorial_team(scene, seed)
    members = {item["role"]: item for item in team["members"]}
    evidence = _json_object(generator.generate_prompt(_evidence_prompt(members["evidence"], source, task, scene, contract)))
    evidence.setdefault("score", 0); evidence.setdefault("confidence", 0.5); evidence.setdefault("veto", False)
    writer = _json_object(generator.generate_prompt(_writer_prompt(members["writer"], source, task, scene, contract, evidence)))
    writer.setdefault("score", 0); writer.setdefault("confidence", 0.5); writer.setdefault("text", source)
    final_review = _json_object(generator.generate_prompt(_review_prompt(members["final_review"], source, task, scene, contract, evidence, writer.get("text", ""))))
    final_review.setdefault("score", 0); final_review.setdefault("confidence", 0.5); final_review.setdefault("veto", False)
    role_results = {"evidence": _role_result(members["evidence"], evidence), "writer": _role_result(members["writer"], writer), "final_review": _role_result(members["final_review"], final_review)}
    team_score = round(sum(float(role_results[role]["score"]) * 20 * TEAM_WEIGHTS[role] for role in TEAM_WEIGHTS), 1)
    vetoes = [role for role in ("evidence", "final_review") if role_results[role].get("veto")]
    return {"institution": "SevenWriter 三人编辑部", "seed": team["seed"], "scene": scene, "members": team["members"], "results": role_results, "team_score_100": 0.0 if vetoes else team_score, "status": "reject" if vetoes else "review", "vetoes": vetoes, "candidate": writer.get("text", ""), "aggregation": "资料校核30% + 场景主笔20% + 独立终审50%；资料校核与独立终审可否决", "isolation_notice": "运行时通过独立调用隔离阶段；宿主支持子代理时，应让资料校核和独立终审保持只读，并让终审使用新上下文。"}


def combine_with_sevenwriter(rubric_score: float, team: dict) -> dict:
    if team.get("status") == "reject": return {"status": "reject", "total": 0.0, "rubric": rubric_score, "team": team.get("team_score_100")}
    return {"status": "review", "total": round(rubric_score * 0.70 + float(team.get("team_score_100", 0)) * 0.30, 1), "rubric": rubric_score, "team": team.get("team_score_100")}


def _role_result(member, result):
    return {"role": member["role"], "role_label": member["role_label"], "reviewer_id": member["id"], "name": member["name"], "score": max(0, min(5, float(result.get("score", 0)))), "confidence": max(0, min(1, float(result.get("confidence", 0.5)))), "veto": bool(result.get("veto", False)) if member["role"] != "writer" else False, "rationale": str(result.get("rationale", "")), "strengths": list(result.get("strengths", [])), "issues": list(result.get("issues", [])), "delivery_advice": str(result.get("delivery_advice", "")), "evidence_packet": result.get("evidence_packet"), "change_log": list(result.get("change_log", [])), "self_check": result.get("self_check")}


def _evidence_prompt(member, source, task, scene, contract):
    return "你是 SevenWriter 的资料校核席，只读，不改写正文。核对材料、来源、时效、事实、未知项和内容契约。只输出 JSON 对象：score(0-5), confidence(0-1), veto, rationale, strengths, issues, evidence_packet。evidence_packet 包含 confirmed_facts, unknowns, locks, scene_requirements, sources_to_verify。材料不足时可以 veto。\n" + _payload(member, source, task, scene, contract)


def _writer_prompt(member, source, task, scene, contract, evidence):
    return "你是 SevenWriter 的场景主笔席。只使用原始材料、内容契约和资料校核包完成任务。原稿已优秀时允许原文胜出。只输出 JSON 对象：text, score(0-5), confidence(0-1), rationale, strengths, issues, change_log, self_check。不得否决自己的稿件。\n" + json.dumps({"member": member, "task": task, "scene": scene, "contract": contract, "source": source, "evidence_packet": evidence.get("evidence_packet", {}), "evidence_issues": evidence.get("issues", [])}, ensure_ascii=False, indent=2)


def _review_prompt(member, source, task, scene, contract, evidence, candidate):
    return "你是 SevenWriter 的独立终审席，只读并从新上下文判断。你看不到主笔策略、自评分或先前排名。只输出 JSON 对象：score(0-5), confidence(0-1), veto, rationale, strengths, issues, delivery_advice。issues 每项包含 priority, location, quote, problem, reason, suggested_change, example, verification, needs_human_confirmation。事实、伦理、合规或关键契约错误可 veto。\n" + json.dumps({"member": member, "task": task, "scene": scene, "contract": contract, "source": source, "confirmed_evidence": evidence.get("evidence_packet", {}), "candidate": candidate}, ensure_ascii=False, indent=2)


def _payload(member, source, task, scene, contract): return json.dumps({"member": member, "task": task, "scene": scene, "contract": contract, "source": source}, ensure_ascii=False, indent=2)


def _json_object(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match: raise ValueError("三人编辑部成员没有返回 JSON 对象")
    value = json.loads(match.group(0))
    if not isinstance(value, dict): raise ValueError("三人编辑部返回值必须是 JSON 对象")
    return value
