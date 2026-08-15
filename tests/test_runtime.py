from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from runtime.contract import infer_contract, validate_contract
from runtime.document import map_markdown, merge_sections
from runtime.docx import apply_docx_replacements, extract_docx
from runtime.pipeline import prepare_job, run_pipeline
from runtime.generator import Generator
from runtime.jury import SCENE_BRIEFS, aggregate, combined_score, select_panel, select_roles
from runtime.style import extract_style
from runtime.router import SCENE_HINTS, SUBSCENE_HINTS, route
from runtime.report import build_revision_plan, render_report
from runtime.team import combine_with_sevenwriter, select_editorial_team


class RuntimeTests(unittest.TestCase):
    def test_contract(self):
        source = "预计 2026 年完成，详情 https://example.com。"
        contract = infer_contract(source)
        self.assertFalse(validate_contract(source, "已经完成。", contract)["passed"])

    def test_style(self):
        profile = extract_style(["我先确认。晚点回复你。\n\n这件事不复杂。"])
        self.assertEqual(profile["samples"], 1)

    def test_markdown(self):
        source = "# 标题\n\n正文\n## 二级\n内容\n"
        mapped = map_markdown(source)
        self.assertEqual(len(mapped["sections"]), 2)
        self.assertIn("新内容", merge_sections(source, {"s2": "## 二级\n新内容\n"}))

    def test_prepare_job(self):
        job = prepare_job("原文", "自然改写", "email")
        self.assertGreaterEqual(len(job["requests"]), 2)

    def test_url_is_not_automatically_seo(self):
        routed = route("请读取 https://example.com 后帮我写一篇介绍")
        self.assertEqual(routed.source_kind, "url")
        self.assertEqual(routed.scene, "website")
        self.assertFalse(routed.explicit_optimization)
        self.assertEqual(route("分析这个页面的 SEO").scene, "seo")

    def test_extended_scene_and_capability_routing(self):
        self.assertEqual(route("写一份项目周报").scene, "weekly-report")
        self.assertEqual(route("检查广告投放合规").scene, "compliance")
        self.assertEqual(route("润色论文摘要").scene, "academic")
        self.assertEqual(route("写一篇公众号文章").scene, "wechat-official-account")
        self.assertEqual(route("帮我改朋友圈文案").scene, "wechat-moments")
        routed = route("把这篇博客去 AI 味，并检查可读性和一致性")
        self.assertEqual(set(routed.capabilities), {"humanize", "readability", "consistency"})
        self.assertTrue(set(SCENE_HINTS).issubset(SCENE_BRIEFS))
        self.assertTrue(set(SUBSCENE_HINTS).issubset(SCENE_BRIEFS))

    def test_review_report(self):
        run = {"selected": {"name": "natural", "text": "成稿", "score": {"total": 88, "dimensions": {"faithfulness": 5, "naturalness": 4.2}, "failures": [], "warnings": [{"tag": "scene.length"}], "evidence": {"analysis": {"findings": []}}}}, "history": []}
        plan = build_revision_plan(run)
        self.assertEqual(plan["status"], "revise")
        self.assertIn("最终文案", render_report(run, plan))

    def test_detailed_score_and_actionable_report(self):
        from runtime.scorer import score
        result = score("预计明天下午回复。", "预计明天下午回复。", "email").to_dict()
        self.assertEqual(set(result["dimension_details"]), {"faithfulness", "scene_fit", "naturalness", "density", "style_match", "readability", "pattern_risk"})
        self.assertTrue(all("improve" in item and "weighted_score" in item for item in result["dimension_details"].values()))
        run = {"job": {"effective_scene": "email"}, "selected": {"name": "baseline", "text": "预计明天下午回复。", "score": result}, "history": []}
        plan = build_revision_plan(run)
        report = render_report(run, plan)
        self.assertIn("得分理由", report)
        self.assertIn("发布或发送前检查", report)
        self.assertIn("建议改法", report)

    def test_jury_reason_is_rendered(self):
        result = {"total": 88, "dimensions": {}, "failures": [], "warnings": [], "evidence": {"analysis": {"findings": []}}, "council": {"ballots": [{"title": "许知衡", "score": 4.2, "confidence": 0.9, "veto": False, "rationale": "事实保留完整，但一处主张缺少来源。", "strengths": ["数字未改"], "evidence": ["第2段"], "issues": [], "delivery_advice": "补充来源后发布"}]}}
        run = {"job": {"effective_scene": "seo"}, "selected": {"name": "natural", "text": "成稿", "score": result}, "history": []}
        report = render_report(run, build_revision_plan(run))
        self.assertIn("为什么是这个分数：事实保留完整", report)
        self.assertIn("补充来源后发布", report)

    def test_academic_target_readiness_is_separate(self):
        from runtime.scorer import score
        contract = infer_contract("研究摘要", {"metadata": {"academic": {"publisher": "ACS", "jcr": {"quartile": "Q1"}, "cas_partition": {"year": "2026"}, "indexing": {"collection": "SCIE"}}}})
        result = score("研究摘要", "研究摘要", "academic", contract).to_dict()
        academic = result["evidence"]["academic_target"]
        self.assertFalse(academic["affects_writing_quality_total"])
        self.assertTrue(any("2026" in item for item in academic["warnings"]))
        self.assertTrue(any("ACS" in item for item in academic["warnings"]))
        self.assertIn("components", academic)

    def test_academic_metrics_require_multi_year_context(self):
        from runtime.academic import assess_academic_target
        result = assess_academic_target({"academic": {"as_of_date": "2028-08-16", "target_journal": "Example", "article_type": "Article", "guidelines_url": "https://example.com", "guidelines_checked_at": "2028-08-16", "journal_scope": "Chemistry", "jcr_history": [{"release_year": 2028, "metric_year": 2027, "category": "Chemistry", "quartile": "Q1", "jif": 8.1}], "cas_partition_history": [{"year": 2026, "major_quartile": 1}]}})
        self.assertTrue(any("单年" in item for item in result["metric_trends"]["warnings"]))
        self.assertTrue(any("2026" in item for item in result["metric_trends"]["warnings"]))
        self.assertEqual(result["metric_trends"]["latest_metric_year"], 2027)

    def test_jury_fidelity_veto(self):
        ballots = [
            {"seat": "fidelity", "candidate_id": "A", "score": 1, "confidence": 1, "veto": True},
            {"seat": "expression", "candidate_id": "A", "score": 5, "confidence": 1, "veto": False},
            {"seat": "fidelity", "candidate_id": "B", "score": 4, "confidence": 1, "veto": False},
            {"seat": "expression", "candidate_id": "B", "score": 4, "confidence": 1, "veto": False},
        ]
        result = aggregate(ballots, ["A", "B"])
        self.assertEqual(result["winner"], "B")
        self.assertEqual(result["results"]["A"]["status"], "reject")
        self.assertEqual(select_roles("seo", seed=7), ["fidelity", "scene", "expression"])
        panel_a = select_panel("seo", seed=7)
        panel_b = select_panel("seo", seed=8)
        self.assertEqual(len(panel_a["members"]), 3)
        self.assertEqual(set(panel_a["coverage"]), {"事实与边界", "场景与读者", "表达与文风"})
        self.assertNotEqual([m["reviewer_id"] if "reviewer_id" in m else m["id"] for m in panel_a["members"]], [m["id"] for m in panel_b["members"]])
        for scene in SCENE_BRIEFS:
            panel = select_panel(scene, seed=42)
            self.assertEqual(len(panel["members"]), 3)
            self.assertEqual({m["function"] for m in panel["members"]}, {"fidelity", "scene", "expression"})
            self.assertTrue(all("*" in m["scenes"] or scene in m["scenes"] for m in panel["members"]))
        self.assertEqual(combined_score(90, 80)["total"], 87.0)

    def test_editorial_team_roles_and_score(self):
        team = select_editorial_team("seo", seed=7)
        self.assertEqual([m["role"] for m in team["members"]], ["evidence", "writer", "final_review"])
        self.assertEqual({m["role_label"] for m in team["members"]}, {"资料校核席", "场景主笔席", "独立终审席"})
        combined = combine_with_sevenwriter(90, {"status": "review", "team_score_100": 78})
        self.assertEqual(combined["total"], 86.4)
        self.assertEqual(combine_with_sevenwriter(90, {"status": "reject", "team_score_100": 0})["status"], "reject")

    def test_editorial_team_report_explains_each_seat(self):
        role = lambda label, name, score, rationale: {"role_label": label, "name": name, "score": score, "confidence": .9, "veto": False, "rationale": rationale, "strengths": ["通过项"], "issues": [], "delivery_advice": "可进入下一步", "evidence_packet": None, "change_log": [], "self_check": None}
        team = {"team_score_100": 84, "status": "review", "results": {"evidence": role("资料校核席", "唐砚舟", 4.5, "来源与锁定项完整。"), "writer": role("场景主笔席", "顾行简", 4.0, "完成了任务与场景要求。"), "final_review": role("独立终审席", "温书晴", 4.1, "成稿可读且没有关键风险。")}}
        result = {"total": 88, "combined": {"rubric": 88, "team": 84, "total": 86.8}, "dimensions": {}, "failures": [], "warnings": [], "evidence": {"analysis": {"findings": []}}, "team": team}
        run = {"job": {"effective_scene": "seo"}, "team": team, "selected": {"name": "editorial-team", "text": "成稿", "score": result}, "history": []}
        report = render_report(run, build_revision_plan(run))
        self.assertIn("唐砚舟 · 资料校核席", report)
        self.assertIn("顾行简 · 场景主笔席", report)
        self.assertIn("温书晴 · 独立终审席", report)
        self.assertIn("来源与锁定项完整", report)

    def test_editorial_team_pipeline_writes_artifacts(self):
        class StubGenerator(Generator):
            def __init__(self): self.calls = 0
            def generate_prompt(self, prompt):
                self.calls += 1
                if self.calls == 1:
                    return json.dumps({"score": 4.5, "confidence": .9, "veto": False, "rationale": "材料足够。", "strengths": ["时间已锁定"], "issues": [], "evidence_packet": {"confirmed_facts": ["预计明天下午回复"], "unknowns": [], "locks": ["明天下午"], "scene_requirements": ["不确定性"], "sources_to_verify": []}}, ensure_ascii=False)
                if self.calls == 2:
                    return json.dumps({"text": "您好，预计明天下午给您回复。如有其他问题，也可以随时联系我们。", "score": 4.2, "confidence": .8, "rationale": "保留预计和时间。", "strengths": ["承诺边界未变"], "issues": [], "change_log": ["压缩重复表达"], "self_check": {"locks_preserved": True}}, ensure_ascii=False)
                return json.dumps({"score": 4.4, "confidence": .9, "veto": False, "rationale": "事实与语气均可接受。", "strengths": ["保留联系入口"], "issues": [], "delivery_advice": "核对收件人后发送"}, ensure_ascii=False)
        with tempfile.TemporaryDirectory() as tmp:
            result = run_pipeline("预计明天下午给您回复。", "改成客户邮件", "email", StubGenerator(), Path(tmp), team_generator=StubGenerator())
            self.assertEqual(result["schema"], "sevenwriter.run.v3")
            self.assertTrue(result["team"])
            self.assertTrue((Path(tmp) / "review-report.md").exists())
            self.assertIn("独立终审席", (Path(tmp) / "review-report.md").read_text(encoding="utf-8"))

    def test_docx_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, repl, output = Path(tmp)/"a.docx", Path(tmp)/"r.json", Path(tmp)/"b.docx"
            xml = '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>原文</w:t></w:r></w:p></w:body></w:document>'
            with zipfile.ZipFile(source, "w") as archive: archive.writestr("word/document.xml", xml)
            mapped = extract_docx(source); self.assertEqual(mapped["paragraphs"][0]["text"], "原文")
            repl.write_text(json.dumps({mapped["paragraphs"][0]["id"]: "改写"}, ensure_ascii=False), encoding="utf-8")
            apply_docx_replacements(source, repl, output)
            self.assertEqual(extract_docx(output)["paragraphs"][0]["text"], "改写")


if __name__ == "__main__": unittest.main()
