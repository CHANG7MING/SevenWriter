from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass

REVIEWER_POOL = {
    "fidelity": [
        {"id": "tang-yanzhou", "name": "唐砚舟", "scenes": ["*"], "focus": "逐项追踪事实、数字、时间、引用和材料来源。"},
        {"id": "shen-chengyi", "name": "沈澄一", "scenes": ["email", "customer-progress", "after-sales", "interview-followup", "community-notice", "wechat-message"], "focus": "检查状态、承诺、未知项、适用范围和沟通风险。"},
        {"id": "xu-zhiheng", "name": "许知衡", "scenes": ["seo", "geo", "website", "longform", "self-media-longform", "wechat-official-account", "weekly-report", "agreement", "ppt", "academic", "compliance"], "focus": "检查实体、来源、关键词、链接、结构和跨节一致性。"},
    ],
    "scene": [
        {"id": "luo-wenlan", "name": "罗闻岚", "scenes": ["*"], "focus": "从读者关系、知识基础、行动成本和任务完成度审查。"},
        {"id": "qiao-yuan", "name": "乔予安", "scenes": ["xiaohongshu", "wechat-moments", "wechat-official-account", "short-video", "speech", "podcast", "product-recommendation", "self-media-longform", "bio", "game-copy", "ppt"], "focus": "检查社交与口头内容的受众、渠道节奏、说服边界和行动设计。"},
        {"id": "gu-xingjian", "name": "顾行简", "scenes": ["seo", "geo", "website", "longform", "email", "customer-progress", "after-sales", "interview-followup", "community-notice", "weekly-report", "agreement", "academic", "compliance"], "focus": "检查内容是否回答核心问题、兑现目标并给出合适下一步。"},
    ],
    "expression": [
        {"id": "wen-shuqing", "name": "温书晴", "scenes": ["*"], "focus": "检查信息层级、指代、重复、句子负担和逻辑衔接。"},
        {"id": "lin-yuebai", "name": "林月白", "scenes": ["xiaohongshu", "wechat-moments", "wechat-official-account", "product-recommendation", "self-media-longform", "website", "email", "wechat-message", "bio", "game-copy", "podcast"], "focus": "检查自然度、语体、样文匹配和人格边界。"},
        {"id": "he-tingchuan", "name": "何听川", "scenes": ["short-video", "speech", "podcast", "community-notice", "customer-progress", "after-sales", "interview-followup", "longform", "weekly-report", "ppt", "academic", "agreement"], "focus": "检查句段节奏、停顿、听觉重复和机械模板。"},
    ],
}

SCENE_BRIEFS = {
    "seo": {"fidelity": "锁定关键词、实体、URL、引用和可验证声明。", "scene": "检查搜索意图、信息增益、标题层级、锚文本和问题覆盖。", "expression": "检查可扫描性、关键词自然度和避免同义复述。"},
    "geo": {"fidelity": "锁定实体关系、来源、数字、时间和不确定性。", "scene": "检查直接答案、定义边界、可引用性和追问覆盖。", "expression": "检查答案是否独立可读、具体且没有空话。"},
    "email": {"fidelity": "锁定承诺、时间、金额、附件、负责人和当前状态。", "scene": "检查关系距离、邮件目的、下一步和所需回复。", "expression": "检查是否简洁、自然、礼貌但没有客服套话。"},
    "customer-progress": {"fidelity": "核对当前状态、阻塞、承诺时间和负责人。", "scene": "先回答进度，再给下一步或下次同步时间。", "expression": "避免推诿、模糊承诺和重复致歉。"},
    "after-sales": {"fidelity": "核对订单、金额、退款/物流状态、政策和时间。", "scene": "区分已受理、处理中、已退款和到账，并说明用户动作。", "expression": "保持清楚和克制，不用安抚话术代替解决方案。"},
    "interview-followup": {"fidelity": "核对岗位、面试时间、联系人和真实截止日期。", "scene": "检查询问是否明确、礼貌且不施压。", "expression": "保持专业简短，不虚构其他 offer。"},
    "wechat-message": {"fidelity": "保留关键信息、时间和承诺。", "scene": "检查是否适合即时消息的长度与关系。", "expression": "结论优先，避免公文腔、客服腔和强行表情。"},
    "community-notice": {"fidelity": "核对对象、事项、时间、地点/入口和截止时间。", "scene": "检查成员是否能立即知道要做什么。", "expression": "重要变更醒目，避免写成营销文章。"},
    "product-recommendation": {"fidelity": "核对功能、价格、效果、限制、数据和评价来源。", "scene": "检查适用对象、问题、证据和下一步。", "expression": "避免绝对化承诺、伪亲测和广告腔。"},
    "xiaohongshu": {"fidelity": "核对亲历、产品效果、价格、数据和合作身份。", "scene": "检查对象、具体细节、平台阅读节奏和标签相关性。", "expression": "像真实分享但不堆热词、感叹号和假口语。"},
    "short-video": {"fidelity": "核对口播中的事实、产品效果、案例和画面对应。", "scene": "检查前几秒、信息递进、画面节点和结尾动作。", "expression": "检查朗读、呼吸和听觉重复，不随机切短句。"},
    "speech": {"fidelity": "核对引语、故事、数字、时间和舞台材料。", "scene": "检查听众、时长、主线、开场和落点。", "expression": "大声朗读是否自然，停顿和重复是否服务理解。"},
    "longform": {"fidelity": "核对跨章节数字、术语、引用和结论一致性。", "scene": "检查章节作用、全局主线、重复和文档结构。", "expression": "检查段落推进、标题风格和跨节衔接。"},
    "self-media-longform": {"fidelity": "核对案例、数据、亲历、引语和商业合作身份。", "scene": "检查读者问题、文章主线、信息增量和发布渠道。", "expression": "检查段落推进、作者语体和结尾任务，不套统一爆款结构。"},
    "wechat-official-account": {"fidelity": "核对标题承诺、案例、数据、引语、图片来源和商业合作身份。", "scene": "检查订阅读者、打开理由、文章主线、段落信息增量和文末动作。", "expression": "检查标题与摘要、移动端段落、作者语气和结尾，不套统一爆款模板。"},
    "wechat-moments": {"fidelity": "核对亲历、人物、时间、产品效果、图片说明和合作身份。", "scene": "检查好友关系、发布目的、可见范围、长度和互动预期。", "expression": "像发布者本人说话，克制营销腔、排比、标签和强行感悟。"},
    "website": {"fidelity": "核对产品能力、数据、客户引语、价格和限制。", "scene": "检查页面目标、用户阶段、信息层级和 CTA。", "expression": "价值具体、可扫描，不用空泛领先词。"},
    "podcast": {"fidelity": "核对人物、引语、数据、节目事实和口播赞助信息。", "scene": "检查听众、节目时长、段落推进、主持与嘉宾分工。", "expression": "适合听觉接收，转场自然，不把书面长句直接搬入口播。"},
    "weekly-report": {"fidelity": "核对完成项、进度、指标、负责人、风险和日期。", "scene": "区分本周结果、问题、下周计划和需要协助事项。", "expression": "结论优先、可扫描，不用忙碌感代替有效进展。"},
    "agreement": {"fidelity": "核对主体、定义、权利义务、金额、期限、例外和引用条款。", "scene": "检查适用对象、执行条件、违约后果和争议处理是否明确。", "expression": "术语一致、指代唯一、义务主体清楚；不把语言优化冒充法律意见。"},
    "ppt": {"fidelity": "核对数字、图表口径、来源、结论和讲者备注。", "scene": "检查单页任务、信息层级、页面衔接与演讲配合。", "expression": "标题给结论，正文精简但不牺牲必要限定条件。"},
    "bio": {"fidelity": "核对身份、经历、机构、职位、作品、奖项和时间。", "scene": "检查使用场合、读者和长度，突出相关信息。", "expression": "具体克制，不堆荣誉词，不虚构第三方评价。"},
    "academic": {"fidelity": "核对研究问题、方法、数据、引文归属、术语、不确定性，以及目标期刊的收录、JCR/JIF 和中科院分区年份与来源。", "scene": "检查体裁规范、论证链、证据边界、学术诚信和具体目标期刊 Author Guidelines；ACS 必须细化到期刊。", "expression": "准确、清楚、克制；不得为自然度改坏术语或伪造引用，也不得用高分区话术夸大研究贡献。"},
    "game-copy": {"fidelity": "核对玩法、概率、奖励、时间、角色设定和版本信息。", "scene": "检查玩家阶段、世界观、交互位置、年龄分级与平台要求。", "expression": "风格服务角色和玩法，不用流行语破坏世界观一致性。"},
    "compliance": {"fidelity": "核对权利来源、商标用法、广告主张、证据、适用地区和监管限定。", "scene": "识别需要法律或合规人员确认的高风险表述，不承诺合规结论。", "expression": "保留限定条件和披露信息，不以润色掩盖风险。"},
    "general": {"fidelity": "核对所有明确事实、数字、时间、引用和承诺。", "scene": "检查读者、目的、渠道和下一步。", "expression": "检查清楚、具体、自然、紧凑和风格一致。"},
}


@dataclass
class Ballot:
    function: str
    reviewer_id: str
    title: str
    candidate_id: str
    score: float
    confidence: float
    veto: bool
    evidence: list
    failure_tags: list
    rationale: str = ""
    strengths: list | None = None
    issues: list | None = None
    delivery_advice: str = ""


def select_panel(scene: str, seed: int | None = None) -> dict:
    actual_seed = seed if seed is not None else random.SystemRandom().randrange(1, 2**63)
    rng = random.Random(actual_seed)
    members = []
    for function in ("fidelity", "scene", "expression"):
        eligible = [member for member in REVIEWER_POOL[function] if "*" in member["scenes"] or scene in member["scenes"]]
        member = dict(rng.choice(eligible))
        member["function"] = function
        member["scene_brief"] = SCENE_BRIEFS.get(scene, SCENE_BRIEFS["general"])[function]
        members.append(member)
    return {"seed": actual_seed, "scene": scene, "members": members, "coverage": ["事实与边界", "场景与读者", "表达与文风"]}


def select_roles(scene: str, seed: int | None = None) -> list[str]:
    return [m["function"] for m in select_panel(scene, seed)["members"]]


def build_ballot_prompt(member: dict, source: str, candidates: dict[str, str], scene: str, task: str, contract: dict) -> str:
    veto_rule = "发现实质事实或契约错误时设置 veto=true。" if member["function"] == "fidelity" else "不得设置事实否决；发现风险写入 failure_tags。"
    return "你是 SevenWriter 三人评审机构的一名具名评审。不得直接改写整篇正文，不得猜测生成策略。只输出 JSON 数组。每项必须包含 candidate_id, score(0-5), confidence(0-1), veto, rationale（说明为什么是这个分数）, strengths, evidence, failure_tags, issues, delivery_advice。issues 每项包含 priority, location, quote, problem, reason, suggested_change, example, needs_human_confirmation。没有可靠替换内容时 example 置空，不得编造。\n" + json.dumps({"reviewer": member["name"], "function": member["function"], "fixed_specialties": member["scenes"], "individual_focus": member["focus"], "scene_brief": member["scene_brief"], "veto_rule": veto_rule, "task": task, "scene": scene, "contract": contract, "source": source, "candidates": candidates}, ensure_ascii=False, indent=2)


def run_jury(generator, source: str, candidates: dict[str, str], scene: str, task: str, contract: dict, seed: int | None = None) -> dict:
    panel = select_panel(scene, seed)
    ballots = []
    for member in panel["members"]:
        raw = generator.generate_prompt(build_ballot_prompt(member, source, candidates, scene, task, contract))
        for item in _parse_json(raw):
            ballots.append(Ballot(member["function"], member["id"], member["name"], str(item["candidate_id"]), _bound(item.get("score", 0), 0, 5), _bound(item.get("confidence", 0.5), 0, 1), bool(item.get("veto", False)) if member["function"] == "fidelity" else False, list(item.get("evidence", [])), list(item.get("failure_tags", [])), str(item.get("rationale", "")), list(item.get("strengths", [])), list(item.get("issues", [])), str(item.get("delivery_advice", ""))))
    result = aggregate([asdict(b) for b in ballots], list(candidates))
    result["panel"] = panel
    return result


def aggregate(ballots: list[dict], candidate_ids: list[str]) -> dict:
    results = {}
    for candidate_id in candidate_ids:
        selected = [b for b in ballots if b["candidate_id"] == candidate_id]
        vetoes = [b for b in selected if (b.get("function") or b.get("seat") or b.get("role")) == "fidelity" and b.get("veto")]
        weighted = [(float(b["score"]), float(b.get("confidence", 1))) for b in selected]
        denominator = sum(confidence for _, confidence in weighted)
        council_score = round(sum(score * confidence for score, confidence in weighted) / denominator * 20, 1) if denominator else None
        results[candidate_id] = {"status": "reject" if vetoes else "review", "council_score_100": council_score, "vetoes": vetoes, "ballots": selected}
    viable = [(cid, value["council_score_100"]) for cid, value in results.items() if value["status"] != "reject" and value["council_score_100"] is not None]
    winner = max(viable, key=lambda x: x[1])[0] if viable else None
    return {"institution": "SevenWriter 三人评审机构", "results": results, "winner": winner, "aggregation": "三名评审置信度加权均分；事实职能评审可否决"}


def combined_score(rubric_score: float, council_score: float | None, veto: bool = False) -> dict:
    if veto:
        return {"status": "reject", "total": 0.0, "rubric": rubric_score, "council": council_score}
    total = rubric_score if council_score is None else round(rubric_score * 0.70 + council_score * 0.30, 1)
    return {"status": "review", "total": total, "rubric": rubric_score, "council": council_score}


def _parse_json(text: str):
    match = re.search(r"\[[\s\S]*\]", text)
    if not match: raise ValueError("评审模型没有返回 JSON 数组")
    return json.loads(match.group(0))


def _bound(value, low, high): return max(low, min(high, float(value)))
