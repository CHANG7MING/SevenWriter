from __future__ import annotations

import re
from dataclasses import dataclass

SCENE_HINTS = {
    "seo": ("seo", "搜索引擎优化", "搜索排名优化", "关键词优化", "search engine optimization"),
    "geo": ("geo 优化", "生成式引擎优化", "生成式搜索优化", "答案引擎优化", "generative engine optimization"),
    "xiaohongshu": ("小红书", "种草", "笔记"),
    "short-video": ("抖音", "快手", "口播", "短视频脚本"),
    "email": ("邮件", "email", "邮件回复", "客户回复"),
    "speech": ("演讲", "演讲稿", "发言", "致辞"),
    "longform": ("markdown 长文", "word 长文", ".docx", "整篇处理", "博客", "自媒体长文"),
    "wechat-official-account": ("公众号文章", "微信公众号", "公众号推文", "公众号长文"),
    "wechat-moments": ("朋友圈文案", "微信朋友圈", "发朋友圈", "朋友圈"),
    "website": ("网站文案", "网页文案", "产品页面", "落地页"),
    "podcast": ("播客", "播客稿", "音频节目", "节目提纲"),
    "weekly-report": ("周报", "工作周报", "项目周报"),
    "agreement": ("协议", "合同", "条款", "用户协议", "隐私政策"),
    "ppt": ("ppt 文案", "ppt文案", "幻灯片文案", "演示文稿"),
    "bio": ("个人简介", "个人介绍", "作者简介", "讲者简介"),
    "academic": ("学术写作", "论文", "摘要", "文献综述", "研究报告", "sci", "scie", "jcr", "影响因子", "中科院分区", "acs 期刊", "acs投稿"),
    "game-copy": ("游戏文案", "游戏文本", "角色台词", "活动公告"),
    "compliance": ("版权合规", "商标合规", "广告合规", "投放合规", "受监管主张", "合规审查"),
}

CAPABILITY_HINTS = {
    "proofread": ("基础纠错", "纠错", "错别字", "病句", "标点检查"),
    "humanize": ("去ai味", "去 ai 味", "降低ai味", "自然一点"),
    "formalize": ("正式写作", "正式一点", "书面表达"),
    "readability": ("可读性", "更好读", "通俗易懂"),
    "consistency": ("一致性", "一致性检查", "术语一致", "前后一致"),
    "idiomatic": ("地道表达", "中文地道", "本地化表达"),
    "colloquial": ("俚语", "流行语", "网络用语"),
}

SUBSCENE_HINTS = {
    "customer-progress": ("催进度", "进度回复", "什么时候完成"),
    "after-sales": ("售后", "退款", "退货", "物流", "快递"),
    "interview-followup": ("面试跟进", "面试结果", "招聘", "hr"),
    "wechat-message": ("微信", "短消息", "私聊"),
    "community-notice": ("社群通知", "群通知", "群公告"),
    "product-recommendation": ("产品推荐", "推荐文案", "种草"),
    "self-media-longform": ("自媒体", "长文案"),
}


@dataclass(frozen=True)
class Route:
    intent: str
    scene: str
    subscene: str | None
    source_kind: str
    explicit_optimization: bool
    confidence: float
    capabilities: tuple[str, ...] = ()


def route(text: str, explicit_scene: str | None = None) -> Route:
    low = text.lower()
    source_kind = _source_kind(low)
    subscene = _subscene(low)
    if explicit_scene:
        return Route(_intent(low), explicit_scene, subscene, source_kind, explicit_scene in {"seo", "geo"}, 1.0, _capabilities(low))
    scores = {scene: sum(h in low for h in hints) for scene, hints in SCENE_HINTS.items()}
    scene, hits = max(scores.items(), key=lambda item: item[1])
    if not hits:
        scene = "website" if source_kind == "url" else "general"
    return Route(_intent(low), scene, subscene, source_kind, scene in {"seo", "geo"} and hits > 0, min(0.95, 0.45 + hits * 0.15), _capabilities(low))


def _capabilities(text: str) -> tuple[str, ...]:
    return tuple(name for name, hints in CAPABILITY_HINTS.items() if any(h in text for h in hints))


def _source_kind(text: str) -> str:
    if re.search(r"https?://", text): return "url"
    if ".docx" in text: return "docx"
    if ".md" in text or "markdown" in text: return "markdown"
    return "inline"


def _subscene(text: str) -> str | None:
    scores = {name: sum(h in text for h in hints) for name, hints in SUBSCENE_HINTS.items()}
    name, hits = max(scores.items(), key=lambda item: item[1])
    return name if hits else None


def _intent(text: str) -> str:
    if any(x in text for x in ("只分析", "诊断", "检查", "audit", "analyze")): return "analyze"
    if any(x in text for x in ("改写", "润色", "优化", "纠错", "校对", "正式写作", "可读性", "地道表达", "去ai", "去 ai", "rewrite")): return "rewrite"
    if any(x in text for x in ("选题", "不知道写什么", "灵感", "ideate")): return "ideate"
    return "create"
