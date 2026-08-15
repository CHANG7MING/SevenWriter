from __future__ import annotations

import json


def build_revision_plan(run: dict) -> dict:
    selected = run["selected"]
    score = selected["score"]
    must_fix, should_fix, keep = [], [], []
    for item in score.get("failures", []):
        must_fix.append(_change_item(item, "P0", "硬门槛失败，修复前不得发布或发送"))
    for item in score.get("warnings", []):
        should_fix.append(_change_item(item, "P1", "需要结合上下文复核"))
    for finding in score.get("evidence", {}).get("analysis", {}).get("findings", []):
        target = must_fix if finding.get("severity") == "FAIL" else should_fix
        target.append({
            "tag": finding.get("tag"), "priority": "P0" if target is must_fix else "P2",
            "location": f"第 {finding.get('line', '?')} 行", "current": finding.get("evidence"),
            "problem": finding.get("message"), "reason": "规则只负责定位，必须确认该表达在当前场景中是否确实无信息价值。",
            "suggested_change": "结合上下文局部改写；若表达具有礼貌、法律限定或结构功能则保留。",
            "example": "", "verification": "复读上下文并与任务目标、内容契约核对", "needs_human_confirmation": True,
        })
    council = score.get("council") or {}
    for veto in council.get("vetoes", []):
        must_fix.append({"tag": "council.veto", "priority": "P0", "reviewer": veto.get("title"), "current": veto.get("evidence"), "problem": "事实与边界评审否决", "reason": veto.get("rationale") or "存在实质事实或契约风险", "suggested_change": "修复后重新提交三人评审", "example": "", "verification": "由材料持有人核对", "needs_human_confirmation": True})
    for ballot in council.get("ballots", []):
        for issue in ballot.get("issues") or []:
            normalized = {"reviewer": ballot.get("title"), **issue}
            normalized.setdefault("priority", "P1")
            normalized.setdefault("verification", "按评审证据复核")
            (must_fix if normalized["priority"] == "P0" else should_fix).append(normalized)
    team = score.get("team") or run.get("team") or {}
    for role in ("evidence", "final_review"):
        role_result = (team.get("results") or {}).get(role) or {}
        if role_result.get("veto"):
            must_fix.append({"tag": f"team.{role}.veto", "priority": "P0", "reviewer": role_result.get("name"), "current": "否决", "problem": f"{role_result.get('role_label', role)}否决", "reason": role_result.get("rationale") or "存在关键风险", "suggested_change": "按问题清单修复后重新提交独立复核", "example": "", "verification": role_result.get("delivery_advice") or "由材料持有人或专业人员核对", "needs_human_confirmation": True})
        for issue in role_result.get("issues") or []:
            normalized = {"reviewer": role_result.get("name"), **issue}
            normalized.setdefault("priority", "P1")
            normalized.setdefault("verification", "按该席位的证据与建议复核")
            (must_fix if normalized["priority"] == "P0" else should_fix).append(normalized)
    for dimension, detail in (score.get("dimension_details") or {}).items():
        if detail.get("score_5", 0) >= 4:
            keep.append({"dimension": detail.get("label", dimension), "score_5": detail.get("score_5"), "reason": detail.get("positive", [])})
    rejected = _rejected_candidates(run, selected)
    status = "blocked" if must_fix else "revise" if should_fix else "ready"
    scene = run.get("job", {}).get("effective_scene", run.get("job", {}).get("scene", "general"))
    return {"status": status, "selected": selected["name"], "scene": scene, "must_fix": _dedupe(must_fix), "should_fix": _dedupe(should_fix), "keep": _dedupe(keep), "rejected_candidates": rejected, "delivery_checklist": _delivery_checklist(scene, status)}


def render_report(run: dict, plan: dict) -> str:
    selected, score = run["selected"], run["selected"]["score"]
    combined = score.get("combined") or {"total": score.get("total"), "rubric": score.get("total"), "council": None, "team": None}
    institution_score = combined.get("team") if combined.get("team") is not None else combined.get("council")
    lines = ["# SevenWriter 可执行评审报告", "", f"- 选中版本：`{selected['name']}`", f"- 场景：`{plan.get('scene', 'general')}`", f"- 交付状态：`{plan['status']}`", f"- SevenWriter 评分：{combined.get('rubric')}/100", f"- 三人编辑部/评审机构评分：{institution_score if institution_score is not None else '未启用'}", f"- 合并评分：{combined.get('total')}/100", "", "## 一、SevenWriter 分项评分与理由", ""]
    details = score.get("dimension_details") or {}
    if details:
        for _, item in details.items():
            lines.extend([f"### {item['label']}：{item['weighted_score']}/{item['weight']}（原始 {item['score_5']}/5）", "", f"- 得分理由：{_display(item.get('positive'))}", f"- 扣分理由：{_display(item.get('deductions'))}", f"- 证据：{_display(item.get('evidence'))}", f"- 提升条件：{item.get('improve', '无')}", ""])
    else:
        lines.extend(["| 维度 | 得分（5分制） |", "|---|---:|"] + [f"| {k} | {v} |" for k, v in score.get("dimensions", {}).items()] + [""])
    lines.extend(["## 二、三位评审员的独立意见", ""])
    academic = score.get("evidence", {}).get("academic_target")
    if academic:
        lines.extend(["## 学术目标期刊与投稿准备度", "", f"- 准备度：{academic.get('submission_readiness_100')}/100（不计入写作总分）", f"- 状态：{academic.get('status')}", f"- 缺失信息：{_display(academic.get('missing'))}", f"- 风险提示：{_display(academic.get('warnings'))}", f"- 已核验信息：{_display(academic.get('verified_context'))}", f"- 说明：{academic.get('notice')}", ""])
    team = score.get("team") or run.get("team") or {}
    for role in ("evidence", "writer", "final_review"):
        item = (team.get("results") or {}).get(role)
        if not item: continue
        lines.extend([f"### {item.get('name', '成员')} · {item.get('role_label', role)}", "", f"- 个人评分：{round(float(item.get('score', 0))*20, 1)}/100", f"- 评分理由：{item.get('rationale') or '未提供，报告不完整'}", f"- 认可部分：{_display(item.get('strengths'))}", f"- 问题与建议：{_display(item.get('issues'))}", f"- 否决：{'是' if item.get('veto') else '否'}", f"- 发布/发送意见：{item.get('delivery_advice') or '未提供'}"])
        if item.get("evidence_packet") is not None: lines.append(f"- 证据包：{_display(item.get('evidence_packet'))}")
        if item.get("change_log"): lines.append(f"- 主笔变更记录：{_display(item.get('change_log'))}")
        if item.get("self_check") is not None: lines.append(f"- 主笔执行自检：{_display(item.get('self_check'))}")
        lines.append("")
    ballots = (score.get("council") or {}).get("ballots", [])
    if not ballots and not team:
        lines.append("本次未启用三人评审机构。高风险、候选差异较大或用户要求完整报告时应启用。")
    for ballot in ballots:
        lines.extend([f"### {ballot.get('title', ballot.get('reviewer_id', '评审员'))}", "", f"- 个人评分：{round(float(ballot.get('score', 0))*20, 1)}/100", f"- 为什么是这个分数：{ballot.get('rationale') or '评审未提供理由，报告不完整'}", f"- 认可部分：{_display(ballot.get('strengths'))}", f"- 证据：{_display(ballot.get('evidence'))}", f"- 问题与建议：{_display(ballot.get('issues'))}", f"- 否决：{'是' if ballot.get('veto') else '否'}", f"- 发布/发送意见：{ballot.get('delivery_advice') or '未提供'}", ""])
    _append_change_table(lines, "三、必须修改", plan["must_fix"])
    _append_change_table(lines, "四、建议修改", plan["should_fix"])
    _append_items(lines, "五、建议保留", plan["keep"])
    _append_items(lines, "六、未采用候选及原因", plan["rejected_candidates"])
    _append_items(lines, "七、发布或发送前检查", plan.get("delivery_checklist", []))
    lines.extend(["## 八、最终文案", "", selected["text"], ""])
    return "\n".join(lines)


def _change_item(item, priority, reason):
    item = item if isinstance(item, dict) else {"tag": str(item)}
    tag = item.get("tag", "unknown")
    current = item.get("value") or item.get("candidate") or item
    suggestions = {
        "faithfulness.lock": "恢复被遗漏的锁定内容，保持原有含义与限定条件。",
        "faithfulness.soft_lock": "恢复该概念，允许调整位置和表达形式。",
        "faithfulness.modality": "恢复‘预计、可能、已经、尚未’等状态和确定性边界。",
        "document.structure": "恢复标题、链接、表格、代码块或引用结构。",
        "scene.length": "核对篇幅变化是否由任务需要造成；无必要时收回过度扩写或删减。",
        "scene.fit": "补充当前场景完成任务所需的信息，不添加无来源事实。",
    }
    return {"tag": tag, "priority": priority, "location": item.get("location", "需在正文中定位"), "current": current, "problem": item.get("message", tag), "reason": reason, "suggested_change": suggestions.get(tag, "结合证据局部修复，保持其他通过部分不变。"), "example": "", "verification": "与原始材料、内容契约和场景要求逐项核对", "needs_human_confirmation": tag.startswith("faithfulness")}


def _delivery_checklist(scene, status):
    common = ["确认事实、数字、日期、姓名、链接和引用均可核验", "确认未把预计、可能或建议改成确定承诺", "确认最终版本符合目标渠道的格式和长度"]
    scene_items = {
        "email": ["复核收件人、主题、称呼、附件、承诺时间和回复动作后再发送"],
        "wechat-message": ["在手机界面预览长度；确认语气适合双方关系"],
        "seo": ["核对 Title、H1、搜索意图、内部链接与真实页面能力；上线后观察收录和 Search Console 数据"],
        "geo": ["核对来源、实体关系、更新时间、直接答案与限制条件"],
        "xiaohongshu": ["确认没有伪亲测、隐瞒合作或未经证实的效果主张"],
        "short-video": ["大声朗读并计时；检查字幕、画面和口播事实一致"],
        "speech": ["完整朗读计时；核对故事、引语、数字与现场指令"],
        "agreement": ["交由授权业务人员或法律专业人员确认条款效果后再签署"],
        "academic": ["逐项核对数据、方法、引用与体例；在 Master Journal List 核验当前收录状态，记录 JCR/JIF 年份与类别；中科院分区只使用可核验的官方历史版本；读取具体目标期刊最新作者指南；不得用语言润色替代学术审查"],
        "compliance": ["由适用地区和行业的合规人员核验主张、证据、披露与发布渠道"],
        "customer-progress": ["确认当前状态、阻塞、责任人和下次同步时间准确；避免把预计写成保证"],
        "after-sales": ["核对订单、退款、物流、质检和到账分别处于什么状态，再发送给客户"],
        "interview-followup": ["核对岗位、面试日期、联系人和真实截止时间；避免施压或虚构其他 offer"],
        "community-notice": ["在目标群预览；复核对象、时间、地点、入口、截止时间和成员动作"],
        "product-recommendation": ["核对价格、功能、效果、适用对象、限制、评价来源和合作披露"],
        "self-media-longform": ["复核标题承诺、案例来源、商业合作、图片版权和发布平台格式"],
        "wechat-official-account": ["在微信移动端预览标题、摘要、封面、段落和文末链接；复核原创声明、图片版权与转载授权"],
        "wechat-moments": ["在发布界面预览折叠位置、配图和可见范围；确认合作身份、定位信息及互动语气适当"],
        "website": ["核对页面能力、价格、客户引语、CTA、链接和限制；在桌面端与移动端预览"],
        "podcast": ["完整朗读并计时；核对主持与嘉宾分工、引语、赞助披露和音频制作提示"],
        "weekly-report": ["核对完成项、指标、负责人、风险、下周动作和需要决策的事项"],
        "ppt": ["逐页核对标题结论、数据口径、图表来源、讲者备注和页面衔接"],
        "bio": ["由本人或资料负责人核对身份、职位、经历、作品、奖项和使用场合"],
        "longform": ["执行跨章节术语、数字、引用、链接、标题层级和结论一致性检查"],
        "game-copy": ["核对版本、活动时间、奖励、概率入口、付费条件、分级和平台规则"],
        "general": ["按目标读者、渠道、目的和行动要求进行一次人工通读"],
    }
    if status == "blocked": common.insert(0, "当前状态为 blocked：不得直接发布或发送")
    return common + scene_items.get(scene, ["按目标读者、渠道和行动目的进行一次人工通读"])


def _rejected_candidates(run, selected):
    rejected = []
    for round_item in run.get("history", []):
        for candidate in round_item.get("candidates", []):
            if candidate["name"] != selected["name"]:
                reason = "未形成至少 2 分的实质提升"
                if candidate["score"].get("status") == "reject": reason = "未通过事实或结构硬门槛"
                rejected.append({"candidate": candidate["name"], "score": _effective_total(candidate["score"]), "reason": reason})
        candidate = round_item.get("candidate")
        if candidate and round_item.get("decision") == "discard": rejected.append({"candidate": candidate["name"], "score": _effective_total(candidate["score"]), "reason": "修复没有形成足够改善或破坏约束"})
    return rejected


def _effective_total(score): return score.get("combined", {}).get("total", score.get("total"))
def _display(value): return json.dumps(value, ensure_ascii=False) if value not in (None, [], "") else "无"
def _dedupe(items):
    seen, result = set(), []
    for item in items:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key not in seen: seen.add(key); result.append(item)
    return result
def _append_items(lines, title, items):
    lines.extend([f"## {title}", ""])
    if not items: lines.append("无。")
    else:
        for item in items: lines.append(f"- {_display(item)}")
    lines.append("")
def _append_change_table(lines, title, items):
    lines.extend([f"## {title}", ""])
    if not items:
        lines.extend(["无。", ""]); return
    lines.extend(["| 优先级 | 位置 | 当前内容 | 问题与原因 | 建议改法 | 参考改文 | 验证方式 | 人工确认 |", "|---|---|---|---|---|---|---|---|"])
    for x in items:
        cells = [x.get("priority", "P1"), x.get("location", "需定位"), _display(x.get("current") or x.get("quote")), f"{x.get('problem', '')}；{x.get('reason', '')}", x.get("suggested_change", ""), x.get("example") or "无可靠替换句", x.get("verification", "复核上下文"), "需要" if x.get("needs_human_confirmation") else "否"]
        lines.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", "<br>") for c in cells) + " |")
    lines.append("")
