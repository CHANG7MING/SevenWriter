from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .contract import Contract, infer_contract
from .generator import GenerationRequest, Generator, build_prompt
from .jury import combined_score, run_jury
from .repair import repair_plan
from .router import route
from .report import build_revision_plan, render_report
from .scorer import score
from .style import extract_style
from .team import combine_with_sevenwriter, run_editorial_team


@dataclass
class Candidate:
    name: str
    text: str
    score: dict
    round: int


def choose_strategies(scene: str, length: int) -> list[str]:
    if scene == "email" and length < 500:
        return ["minimal", "natural"]
    if scene in {"seo", "geo", "speech", "longform", "website"}:
        return ["minimal", "natural", "scene", "structural"]
    return ["minimal", "natural", "scene"]


def prepare_job(source: str, task: str, scene: str, explicit_contract: dict | None = None, style_samples: list[str] | None = None) -> dict:
    routed = route(task, None if scene == "general" else scene)
    effective_scene = routed.subscene or routed.scene
    contract = infer_contract(source, explicit_contract)
    style = extract_style(style_samples) if style_samples else None
    requests = [GenerationRequest(source, task, effective_scene, strategy, contract.to_dict(), style) for strategy in choose_strategies(scene, len(source))]
    return {"schema": "sevenwriter.job.v1", "task": task, "scene": scene, "effective_scene": effective_scene, "route": routed.__dict__, "source": source, "contract": contract.to_dict(), "style": style, "requests": [{"strategy": r.strategy, "prompt": build_prompt(r)} for r in requests]}


def run_pipeline(source: str, task: str, scene: str, generator: Generator, output_dir: Path, explicit_contract: dict | None = None, style_samples: list[str] | None = None, max_rounds: int = 3, council_generator: Generator | None = None, team_generator: Generator | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    job = prepare_job(source, task, scene, explicit_contract, style_samples)
    effective_scene = job["effective_scene"]
    contract = Contract(**job["contract"])
    baseline_score = score(source, source, effective_scene, contract, job["style"]).to_dict()
    if team_generator:
        team = run_editorial_team(team_generator, source, task, effective_scene, job["contract"])
        candidate_text = team["candidate"] or source
        candidate_score = score(candidate_text, source, effective_scene, contract, job["style"]).to_dict()
        candidate_score["team"] = team
        candidate_score["combined"] = combine_with_sevenwriter(candidate_score["total"], team)
        if team["status"] == "reject":
            candidate_score["status"] = "reject"
        selected = Candidate("editorial-team", candidate_text, candidate_score, 1)
        result = {"schema": "sevenwriter.run.v3", "created_at": datetime.now(timezone.utc).isoformat(), "job": job, "baseline_score": baseline_score, "team": team, "council": None, "history": [{"round": 1, "selected": selected.name, "candidates": [_candidate_dict(selected)]}], "selected": _candidate_dict(selected), "external_signals": []}
        return _write_artifacts(result, output_dir)
    candidates: list[Candidate] = []
    for item in job["requests"]:
        req = GenerationRequest(source, task, effective_scene, item["strategy"], job["contract"], job["style"])
        text = generator.generate(req)
        result = score(text, source, effective_scene, contract, job["style"]).to_dict()
        candidates.append(Candidate(item["strategy"], text, result, 1))
    council = None
    if council_generator and candidates:
        anonymous = {chr(65 + index): candidate.text for index, candidate in enumerate(candidates)}
        council = run_jury(council_generator, source, anonymous, effective_scene, task, contract.to_dict())
        for index, candidate in enumerate(candidates):
            council_result = council["results"][chr(65 + index)]
            combined = combined_score(candidate.score["total"], council_result["council_score_100"], council_result["status"] == "reject")
            candidate.score["council"] = council_result
            candidate.score["combined"] = combined
    viable = [c for c in candidates if c.score["status"] != "reject"]
    best = max(viable, key=lambda c: c.score.get("combined", {}).get("total", c.score["total"]), default=Candidate("baseline", source, baseline_score, 0))
    history = [{"round": 1, "selected": best.name, "candidates": [_candidate_dict(c) for c in candidates]}]
    for round_no in range(2, max(1, min(max_rounds, 5)) + 1):
        plan = repair_plan(best.score)
        if not plan or best.score["status"] == "pass":
            break
        req = GenerationRequest(best.text, task, effective_scene, "repair", job["contract"], job["style"], plan)
        repaired = generator.generate(req)
        repaired_score = score(repaired, source, effective_scene, contract, job["style"]).to_dict()
        if council_generator:
            review = run_jury(council_generator, source, {"A": repaired}, effective_scene, task, contract.to_dict())["results"]["A"]
            repaired_score["council"] = review
            repaired_score["combined"] = combined_score(repaired_score["total"], review["council_score_100"], review["status"] == "reject")
        challenger = Candidate(f"repair-{round_no}", repaired, repaired_score, round_no)
        repaired_total = repaired_score.get("combined", {}).get("total", repaired_score["total"])
        best_total = best.score.get("combined", {}).get("total", best.score["total"])
        decision = "keep" if repaired_score["status"] != "reject" and repaired_total >= best_total + 2 else "discard"
        history.append({"round": round_no, "repair_plan": plan, "decision": decision, "candidate": _candidate_dict(challenger)})
        if decision == "keep":
            best = challenger
        else:
            break
    result = {"schema": "sevenwriter.run.v2", "created_at": datetime.now(timezone.utc).isoformat(), "job": job, "baseline_score": baseline_score, "council": council, "history": history, "selected": _candidate_dict(best), "external_signals": []}
    return _write_artifacts(result, output_dir)


def _write_artifacts(result: dict, output_dir: Path) -> dict:
    selected = result["selected"]
    (output_dir / "run.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "final.txt").write_text(selected["text"], encoding="utf-8")
    (output_dir / "final.md").write_text(selected["text"], encoding="utf-8")
    revision_plan = build_revision_plan(result)
    (output_dir / "revision-plan.json").write_text(json.dumps(revision_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "review-report.md").write_text(render_report(result, revision_plan), encoding="utf-8")
    result["artifacts"] = {"copy": str(output_dir / "final.md"), "plain_text": str(output_dir / "final.txt"), "review_report": str(output_dir / "review-report.md"), "revision_plan": str(output_dir / "revision-plan.json"), "run_record": str(output_dir / "run.json")}
    (output_dir / "run.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _candidate_dict(candidate: Candidate) -> dict:
    return asdict(candidate)
