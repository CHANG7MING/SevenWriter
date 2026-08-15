#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.analyzer import analyze
from runtime.contract import Contract, infer_contract, validate_contract
from runtime.document import map_markdown, merge_sections
from runtime.docx import apply_docx_replacements, extract_docx
from runtime.document_pipeline import run_docx, run_markdown
from runtime.generator import CommandGenerator, OpenAICompatibleGenerator
from runtime.jury import run_jury
from runtime.pipeline import prepare_job, run_pipeline
from runtime.repair import repair_plan
from runtime.router import route
from runtime.scorer import score
from runtime.style import extract_style
from runtime.webpage import fetch_page


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


def emit(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def load_json(path: str | None, default=None):
    return json.loads(read(path)) if path else default


def main() -> int:
    parser = argparse.ArgumentParser(description="SevenWriter v0.2 writing quality pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("analyze"); a.add_argument("file"); a.add_argument("--profile")
    f = sub.add_parser("fetch-url"); f.add_argument("url"); f.add_argument("--output", required=True)
    s = sub.add_parser("style"); s.add_argument("files", nargs="+"); s.add_argument("--output")
    ct = sub.add_parser("contract"); ct.add_argument("source"); ct.add_argument("--candidate"); ct.add_argument("--config")
    sc = sub.add_parser("score"); sc.add_argument("file"); sc.add_argument("--source"); sc.add_argument("--profile", default="general"); sc.add_argument("--contract"); sc.add_argument("--style")
    c = sub.add_parser("compare"); c.add_argument("baseline"); c.add_argument("candidate"); c.add_argument("--source"); c.add_argument("--profile", default="general"); c.add_argument("--contract"); c.add_argument("--style")
    m = sub.add_parser("map"); m.add_argument("file")
    mg = sub.add_parser("merge-md"); mg.add_argument("source"); mg.add_argument("replacements"); mg.add_argument("output")
    dx = sub.add_parser("docx-extract"); dx.add_argument("file"); dx.add_argument("--output")
    da = sub.add_parser("docx-apply"); da.add_argument("source"); da.add_argument("replacements"); da.add_argument("output")
    p = sub.add_parser("prepare"); p.add_argument("source"); p.add_argument("--task", required=True); p.add_argument("--profile", default="general"); p.add_argument("--contract"); p.add_argument("--style-sample", action="append"); p.add_argument("--output", required=True)
    run = sub.add_parser("run"); run.add_argument("source"); run.add_argument("--task", required=True); run.add_argument("--profile", default="general"); run.add_argument("--backend", choices=("command", "openai-compatible"), required=True); run.add_argument("--command", dest="backend_command"); run.add_argument("--endpoint"); run.add_argument("--model"); run.add_argument("--api-key-env", default="SEVENWRITER_API_KEY"); run.add_argument("--contract"); run.add_argument("--style-sample", action="append"); run.add_argument("--rounds", type=int, default=3); run.add_argument("--council", action="store_true", help="兼容旧版：候选生成后进行三人盲评"); run.add_argument("--team", action="store_true", help="启用资料校核、场景主笔、独立终审三人编辑部"); run.add_argument("--output-dir", required=True)
    jy = sub.add_parser("jury"); jy.add_argument("source"); jy.add_argument("--candidate", action="append", required=True, help="匿名ID=文件路径，例如 A=a.md"); jy.add_argument("--task", required=True); jy.add_argument("--profile", default="general"); jy.add_argument("--backend", choices=("command", "openai-compatible"), required=True); jy.add_argument("--command", dest="backend_command"); jy.add_argument("--endpoint"); jy.add_argument("--model"); jy.add_argument("--api-key-env", default="SEVENWRITER_API_KEY"); jy.add_argument("--contract"); jy.add_argument("--output")
    dr = sub.add_parser("document-run"); dr.add_argument("source"); dr.add_argument("output"); dr.add_argument("--task", required=True); dr.add_argument("--profile", default="longform"); dr.add_argument("--backend", choices=("command", "openai-compatible"), required=True); dr.add_argument("--command", dest="backend_command"); dr.add_argument("--endpoint"); dr.add_argument("--model"); dr.add_argument("--api-key-env", default="SEVENWRITER_API_KEY"); dr.add_argument("--rounds", type=int, default=3); dr.add_argument("--work-dir", required=True)
    ex = sub.add_parser("external-signal"); ex.add_argument("run_json"); ex.add_argument("--detector", required=True); ex.add_argument("--value", required=True); ex.add_argument("--notes", default="")
    b = sub.add_parser("benchmark"); b.add_argument("file"); b.add_argument("--output")
    ins = sub.add_parser("install"); ins.add_argument("--target", required=True)
    args = parser.parse_args()

    if args.command == "analyze":
        text = read(args.file); result = analyze(text); result["route"] = route(text, args.profile).__dict__; emit(result)
    elif args.command == "fetch-url": _emit_or_write(fetch_page(args.url), args.output)
    elif args.command == "style":
        result = extract_style([read(p) for p in args.files]); _emit_or_write(result, args.output)
    elif args.command == "contract":
        source = read(args.source); contract = infer_contract(source, load_json(args.config, {})); result = contract.to_dict()
        if args.candidate: result["validation"] = validate_contract(source, read(args.candidate), contract)
        emit(result)
    elif args.command == "score":
        result = _score_args(args).to_dict(); result["repair_plan"] = repair_plan(result); emit(result)
    elif args.command == "compare":
        source = read(args.source) if args.source else read(args.baseline); contract = Contract(**load_json(args.contract)) if args.contract else infer_contract(source); style = load_json(args.style)
        left, right = score(read(args.baseline), source, args.profile, contract, style), score(read(args.candidate), source, args.profile, contract, style)
        decision = "reject" if right.status == "reject" else ("keep" if right.total >= left.total + 2 else "discard")
        emit({"baseline": left.to_dict(), "candidate": right.to_dict(), "delta": round(right.total-left.total, 1), "decision": decision})
    elif args.command == "map": emit(map_markdown(read(args.file)))
    elif args.command == "merge-md":
        output = merge_sections(read(args.source), load_json(args.replacements)); Path(args.output).write_text(output, encoding="utf-8"); emit({"output": args.output})
    elif args.command == "docx-extract": _emit_or_write(extract_docx(Path(args.file)), args.output)
    elif args.command == "docx-apply": emit(apply_docx_replacements(Path(args.source), Path(args.replacements), Path(args.output)))
    elif args.command == "prepare":
        job = prepare_job(read(args.source), args.task, args.profile, load_json(args.contract, {}), [read(p) for p in args.style_sample or []]); _emit_or_write(job, args.output)
    elif args.command == "run":
        if args.team and args.council: raise SystemExit("--team 与 --council 不能同时使用")
        generator = _generator(args); result = run_pipeline(read(args.source), args.task, args.profile, generator, Path(args.output_dir), load_json(args.contract, {}), [read(p) for p in args.style_sample or []], args.rounds, generator if args.council else None, generator if args.team else None); emit({"output_dir": args.output_dir, "selected": result["selected"], "rounds": len(result["history"]), "team": bool(result.get("team")), "council": bool(result.get("council"))})
    elif args.command == "jury":
        candidates = {}
        for spec in args.candidate:
            candidate_id, separator, file = spec.partition("=")
            if not separator or not candidate_id or not file: raise SystemExit("--candidate 格式必须是 匿名ID=文件路径")
            candidates[candidate_id] = read(file)
        source = read(args.source); contract = load_json(args.contract, infer_contract(source).to_dict()); result = run_jury(_generator(args), source, candidates, args.profile, args.task, contract); _emit_or_write(result, args.output)
    elif args.command == "document-run":
        generator = _generator(args); source, output, work = Path(args.source), Path(args.output), Path(args.work_dir)
        result = run_docx(source, output, args.task, args.profile, generator, work) if source.suffix.lower() == ".docx" else run_markdown(source, output, args.task, args.profile, generator, work, args.rounds); emit(result)
    elif args.command == "external-signal": emit(_external_signal(Path(args.run_json), args.detector, args.value, args.notes))
    elif args.command == "benchmark": _emit_or_write(benchmark(Path(args.file)), args.output)
    elif args.command == "install": emit(install(ROOT, Path(args.target)))
    return 0


def _score_args(args):
    source = read(args.source) if args.source else ""; contract = Contract(**load_json(args.contract)) if args.contract else infer_contract(source)
    return score(read(args.file), source, args.profile, contract, load_json(args.style))


def _generator(args):
    if args.backend == "command":
        if not args.backend_command: raise SystemExit("--backend command 需要 --command")
        return CommandGenerator(args.backend_command)
    if not args.endpoint or not args.model: raise SystemExit("openai-compatible 后端需要 --endpoint 和 --model")
    return OpenAICompatibleGenerator(args.endpoint, args.model, os.getenv(args.api_key_env))


def _emit_or_write(data, output):
    if output:
        Path(output).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"); emit({"output": output})
    else: emit(data)


def _external_signal(path: Path, detector: str, value: str, notes: str):
    data = json.loads(path.read_text(encoding="utf-8")); data.setdefault("external_signals", []).append({"detector": detector, "value": value, "notes": notes, "affects_quality_score": False}); path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"); return {"updated": str(path), "affects_quality_score": False}


def benchmark(path: Path) -> dict:
    rows, totals = [], []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip(): continue
        case = json.loads(line); candidate = case.get("candidate")
        if candidate is None: rows.append({"id": case.get("id", line_no), "status": "pending", "reason": "candidate 缺失"}); continue
        result = score(candidate, case.get("input", ""), case.get("scene", "general"), infer_contract(case.get("input", ""), case), case.get("style_profile")).to_dict(); rows.append({"id": case.get("id", line_no), **result}); totals.append(result["total"])
    return {"cases": rows, "summary": {"count": len(rows), "scored": len(totals), "mean": round(sum(totals)/len(totals), 2) if totals else None}, "notice": "自动结果需结合 rubric 盲评；外部 detector 不参与质量分。"}


def install(source: Path, target: Path) -> dict:
    resolved_source, resolved_target = source.resolve(), target.resolve()
    if resolved_source == resolved_target or resolved_source in resolved_target.parents: raise ValueError("目标不能位于源目录内部")
    if resolved_target.exists() and any(resolved_target.iterdir()): raise FileExistsError("安装目标必须为空")
    resolved_target.mkdir(parents=True, exist_ok=True)
    for child in resolved_source.iterdir():
        if child.name in {".git", "__pycache__", "runs"}: continue
        if child.is_dir(): shutil.copytree(child, resolved_target / child.name)
        else: shutil.copy2(child, resolved_target / child.name)
    return {"installed": str(resolved_target), "protocol": "SKILL.md + shell", "hosts": ["CoPaw", "OpenClaw", "Claude Code", "Hermes", "Codex"]}


if __name__ == "__main__":
    raise SystemExit(main())
