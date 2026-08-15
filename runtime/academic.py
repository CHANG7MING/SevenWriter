from __future__ import annotations

from datetime import date


CORE_FIELDS = ("as_of_date", "target_journal", "article_type", "guidelines_url", "guidelines_checked_at", "journal_scope")
COMPONENT_WEIGHTS = {"journal_identity": 15, "scope_and_article_type": 15, "manuscript_format": 15, "research_integrity": 20, "reporting_transparency": 15, "data_and_materials": 10, "submission_admin": 10}


def assess_academic_target(metadata: dict | None) -> dict:
    academic = (metadata or {}).get("academic", {})
    missing = [field for field in CORE_FIELDS if not academic.get(field)]
    warnings = _warnings(academic)
    trends = _metric_trends(academic)
    warnings.extend(trends["warnings"])
    components = {
        "journal_identity": _component(academic, ("target_journal", "issn", "publisher", "guidelines_url"), COMPONENT_WEIGHTS["journal_identity"]),
        "scope_and_article_type": _component(academic, ("journal_scope", "article_type", "audience", "contribution_statement"), COMPONENT_WEIGHTS["scope_and_article_type"]),
        "manuscript_format": _component(academic.get("format", {}), ("language", "word_limit", "abstract_limit", "section_order", "reference_style"), COMPONENT_WEIGHTS["manuscript_format"]),
        "research_integrity": _component(academic.get("ethics", {}), ("authorship", "conflict_of_interest", "funding", "ai_disclosure", "duplicate_submission"), COMPONENT_WEIGHTS["research_integrity"]),
        "reporting_transparency": _component(academic.get("reporting", {}), ("study_design", "applicable_guideline", "limitations", "statistics_checked"), COMPONENT_WEIGHTS["reporting_transparency"]),
        "data_and_materials": _component(academic.get("open_science", {}), ("data_availability", "code_availability", "supporting_information"), COMPONENT_WEIGHTS["data_and_materials"]),
        "submission_admin": _component(academic.get("submission", {}), ("cover_letter", "author_information", "orcid", "permissions"), COMPONENT_WEIGHTS["submission_admin"]),
    }
    readiness = max(0, round(sum(x["score"] for x in components.values()) - len(warnings) * 2, 1))
    return {
        "status": "ready" if not missing and not warnings and readiness >= 85 else "verify",
        "submission_readiness_100": readiness,
        "components": components,
        "affects_writing_quality_total": False,
        "missing": missing,
        "warnings": warnings,
        "conditional_checks": _conditional_checks(academic),
        "journal_metrics": _journal_metrics(academic),
        "metric_trends": trends,
        "verified_context": academic,
        "notice": "投稿准备度衡量信息和材料是否齐全，不评价研究价值。分区、影响因子和收录信息不进入 SevenWriter 写作总分。",
    }


def _component(data, fields, weight):
    present = [field for field in fields if data.get(field) not in (None, "", [], {})]
    return {"weight": weight, "score": round(weight * len(present) / len(fields), 1), "present": present, "missing": [x for x in fields if x not in present]}


def _warnings(academic):
    warnings = []
    if academic.get("publisher", "").lower() == "acs" and not academic.get("target_journal"):
        warnings.append("ACS 是出版机构而非统一稿件格式；必须指定具体 ACS 期刊并读取最新 Author Guidelines。")
    jcr = academic.get("jcr", {})
    if any(jcr.get(k) for k in ("quartile", "jif", "category")) and not jcr.get("year"):
        warnings.append("JCR 分区、类别或 JIF 缺少年份。")
    if jcr.get("quartile") and not jcr.get("category"):
        warnings.append("JCR 四分位必须绑定学科类别；同一期刊在不同类别中可能不同。")
    if jcr.get("jif") and not jcr.get("jif_year", jcr.get("year")):
        warnings.append("Journal Impact Factor 缺少指标年份。")
    cas = academic.get("cas_partition", {})
    if cas.get("year"):
        try:
            if int(cas["year"]) >= 2026: warnings.append("中科院文献情报中心已宣布自 2026 年起不再更新发布期刊分区表，不得标注官方 2026+ 分区。")
        except (TypeError, ValueError): warnings.append("中科院分区年份格式无效。")
    if cas and not cas.get("source"): warnings.append("中科院分区缺少官方或机构授权查询来源。")
    indexing = academic.get("indexing", {})
    if indexing and not indexing.get("verified_at"): warnings.append("Web of Science 收录状态具有动态性，需要记录 Master Journal List 核验日期。")
    if academic.get("metrics_used_as_quality_claim"): warnings.append("不得把高影响因子或高分区直接写成论文质量、创新性或可录用性的证据。")
    return warnings


def _journal_metrics(academic):
    return {"indexing_history": academic.get("indexing_history", []), "jcr_history": academic.get("jcr_history", []), "cas_partition_history": academic.get("cas_partition_history", []), "legacy_single_values": {"indexing": academic.get("indexing", {}), "jcr": academic.get("jcr", {}), "cas_partition": academic.get("cas_partition", {})}, "other_rankings": academic.get("other_rankings", {}), "oa_and_cost": academic.get("publication", {})}


def _metric_trends(academic):
    jcr = sorted(academic.get("jcr_history", []), key=lambda x: str(x.get("year", "")))
    indexing = sorted(academic.get("indexing_history", []), key=lambda x: str(x.get("date", x.get("year", ""))))
    cas = sorted(academic.get("cas_partition_history", []), key=lambda x: str(x.get("year", "")))
    warnings = []
    as_of = str(academic.get("as_of_date") or date.today().isoformat())
    as_of_year = _year(as_of) or date.today().year
    if academic.get("target_journal") and len(jcr) < 3:
        warnings.append("JCR/JIF 历史不足 3 个可用年度；不得根据单年数值判断期刊稳定性或趋势。")
    for index, row in enumerate(jcr, 1):
        if not row.get("metric_year", row.get("year")): warnings.append(f"第 {index} 条 JCR 历史缺少指标对应年度。")
        if not row.get("release_year"): warnings.append(f"第 {index} 条 JCR 历史缺少发布年度。")
        if row.get("quartile") and not row.get("category"): warnings.append(f"第 {index} 条 JCR 四分位缺少对应学科类别。")
        if not row.get("source") or not row.get("retrieved_at"): warnings.append(f"第 {index} 条 JCR 历史缺少来源或查询日期。")
    categories = {row.get("category") for row in jcr if row.get("category")}
    if len(categories) > 1:
        warnings.append("JCR 历史中学科类别发生变化或包含多个类别，必须分类别比较，不能直接串联四分位。")
    collections = [row.get("collection") for row in indexing if row.get("collection")]
    if len(set(collections)) > 1:
        warnings.append("Web of Science 收录集合曾发生变化，应说明迁移时间，不能只展示当前状态。")
    invalid_cas = [row for row in cas if _year_at_least(row.get("year"), 2026)]
    if invalid_cas:
        warnings.append("中科院分区历史包含 2026 年及以后记录；官方已停止更新，这些记录不得标为官方中科院分区。")
    jif_values = [(row.get("metric_year", row.get("year")), _number(row.get("jif"))) for row in jcr]
    latest_metric_year = max((_year(row.get("metric_year", row.get("year"))) or 0 for row in jcr), default=0)
    if latest_metric_year and latest_metric_year < as_of_year - 2:
        warnings.append(f"最新 JCR/JIF 指标年度为 {latest_metric_year}，相对查询年份 {as_of_year} 可能过旧；应先查询当时最新官方发布。")
    if not academic.get("as_of_date"):
        warnings.append("缺少任务查询日期 as_of_date，无法判断期刊指标和指南是否为当时最新版本。")
    jif_values = [(year, value) for year, value in jif_values if value is not None]
    direction = "insufficient"
    if len(jif_values) >= 3:
        delta = jif_values[-1][1] - jif_values[0][1]
        direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
    return {"as_of_date": as_of, "latest_metric_year": latest_metric_year or None, "window": "从查询日期对应的最新官方可用年度向前取 3–5 个数据点；不固定某个自然年", "jcr_points": len(jcr), "indexing_points": len(indexing), "cas_legacy_points": len(cas), "jif_direction": direction, "warnings": warnings, "notice": "趋势只描述期刊指标变化，不预测录用概率，也不评价单篇论文质量。"}


def _number(value):
    try: return float(value)
    except (TypeError, ValueError): return None


def _year_at_least(value, threshold):
    try: return int(value) >= threshold
    except (TypeError, ValueError): return False


def _year(value):
    try: return int(str(value)[:4])
    except (TypeError, ValueError): return None


def _conditional_checks(academic):
    design = str(academic.get("reporting", {}).get("study_design", "")).lower()
    checks = []
    mapping = {
        "randomized": "核对试验注册、伦理批准、知情同意和适用的随机试验报告规范。",
        "systematic review": "核对方案注册、检索式、筛选流程、偏倚评估和适用的系统综述报告规范。",
        "observational": "核对样本来源、混杂因素、缺失数据和适用的观察性研究报告规范。",
        "animal": "核对动物伦理、样本量、随机化、盲法和适用的动物研究报告规范。",
        "case report": "核对患者同意、去标识化和适用的病例报告规范。",
    }
    for key, value in mapping.items():
        if key in design: checks.append(value)
    if not design: checks.append("尚未提供研究设计，无法选择对应报告规范。")
    return checks
