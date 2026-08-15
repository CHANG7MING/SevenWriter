PRIORITY = ("faithfulness.", "document.", "scene.", "density.", "naturalness.", "style.")


def repair_plan(score: dict, limit: int = 3) -> list[dict]:
    raw = score.get("failures", []) + score.get("warnings", [])
    tags = []
    for item in raw:
        tag = item.get("tag", "") if isinstance(item, dict) else str(item)
        if tag and tag not in tags:
            tags.append(tag)
    evidence_findings = score.get("evidence", {}).get("analysis", {}).get("findings", [])
    for item in evidence_findings:
        if item.get("tag") not in tags:
            tags.append(item.get("tag"))
    tags.sort(key=lambda tag: next((i for i, prefix in enumerate(PRIORITY) if tag.startswith(prefix)), len(PRIORITY)))
    return [{"tag": tag, "instruction": _instruction(tag)} for tag in tags[:limit] if tag]


def _instruction(tag: str) -> str:
    if tag.startswith("faithfulness"):
        return "对照源文恢复实体、数字、限定语或因果；不要改动其他已通过内容。"
    if tag.startswith("document"):
        return "恢复被破坏的链接或结构标记，并复核相邻内容。"
    if tag.startswith("scene"):
        return "只补足场景必需的对象、动作、结构或边界，不添加未经材料支持的事实。"
    if "contrast" in tag:
        return "只改机械二元转折：直接陈述判断；真实对立关系保留。"
    if "vague" in tag:
        return "把抽象动作替换为材料中可确认的主体、动作和结果。"
    return "在不触碰内容契约的前提下，局部修复该问题并保持其他内容不变。"
