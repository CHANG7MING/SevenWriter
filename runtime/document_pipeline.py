from __future__ import annotations

import json
from pathlib import Path

from .contract import infer_contract, validate_contract
from .document import merge_sections, split_markdown
from .docx import apply_docx_replacements, extract_docx
from .generator import GenerationRequest, Generator
from .pipeline import run_pipeline
from .style import extract_style


def run_markdown(source_path: Path, output_path: Path, task: str, scene: str, generator: Generator, work_dir: Path, max_rounds: int = 3) -> dict:
    source = source_path.read_text(encoding="utf-8-sig")
    sections = split_markdown(source)
    global_style = extract_style([source])
    replacements, ledger = {}, {"headings": [], "locks": infer_contract(source).locks, "sections": []}
    for section in sections:
        ledger["headings"].append(section["heading"])
        section_dir = work_dir / section["id"]
        result = run_pipeline(section["text"], task, scene, generator, section_dir, {"preserve": ["markdown_structure", "code_fences", "urls"], "max_length_delta": 0.25}, [source], max_rounds)
        selected_text = result["selected"]["text"]
        replacements[section["id"]] = selected_text if selected_text.endswith("\n") else selected_text + "\n"
        ledger["sections"].append({"id": section["id"], "selected": result["selected"]["name"], "score": result["selected"]["score"]["total"]})
    merged = merge_sections(source, replacements)
    validation = validate_contract(source, merged, infer_contract(source, {"preserve": ["markdown_structure", "code_fences", "urls"], "max_length_delta": 0.5}))
    if not validation["passed"]:
        raise RuntimeError("合并后的 Markdown 未通过结构/事实契约，拒绝写入最终文件")
    output_path.write_text(merged, encoding="utf-8")
    report = {"source": str(source_path), "output": str(output_path), "sections": len(sections), "style": global_style, "ledger": ledger, "validation": validation}
    (work_dir / "document-run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def run_docx(source_path: Path, output_path: Path, task: str, scene: str, generator: Generator, work_dir: Path) -> dict:
    mapped = extract_docx(source_path)
    replacements = {}
    for paragraph in mapped["paragraphs"]:
        req = GenerationRequest(paragraph["text"], task, scene, "minimal", infer_contract(paragraph["text"]).to_dict())
        candidate = generator.generate(req)
        validation = validate_contract(paragraph["text"], candidate, infer_contract(paragraph["text"], {"max_length_delta": 0.5}))
        if validation["passed"]:
            replacements[paragraph["id"]] = candidate
    work_dir.mkdir(parents=True, exist_ok=True)
    replacements_file = work_dir / "docx-replacements.json"
    replacements_file.write_text(json.dumps(replacements, ensure_ascii=False, indent=2), encoding="utf-8")
    result = apply_docx_replacements(source_path, replacements_file, output_path)
    result.update({"paragraphs_total": len(mapped["paragraphs"]), "paragraphs_changed": len(replacements), "limitations": mapped["limitations"]})
    (work_dir / "document-run.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
