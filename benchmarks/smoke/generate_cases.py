from __future__ import annotations

import json
from pathlib import Path

SCENES = {
    "seo": "# {topic}\n\n在当今数字化时代，{topic} 至关重要。详情见 https://example.com/{n}。",
    "geo": "{topic} 是一个重要概念。根据资料，它可能影响结果，但具体条件尚未说明。",
    "xiaohongshu": "姐妹们，{topic} 真的绝了，闭眼冲！",
    "short-video": "今天介绍 {topic}。首先说明定义，其次介绍优势，最后总结。",
    "email": "您好，关于 {topic}，我们预计明天下午回复。感谢您的理解与支持，如有任何问题请随时联系我们。",
    "speech": "各位好，今天我想谈谈 {topic}。这不仅是一个问题，更是一次重要机会。",
    "website": "{topic} 一站式解决方案，行业领先，立即联系我们了解更多。",
    "longform": "# {topic}\n\n{topic} 非常重要。下面将从多个方面进行全面介绍。",
    "podcast": "欢迎收听本期节目。今天我们将全面聊聊 {topic}，接下来让我们进入正题。",
    "weekly-report": "本周持续推进 {topic}，整体进展顺利，下周将继续积极推进。",
    "agreement": "用户应遵守关于 {topic} 的相关规则，平台拥有最终解释权。",
    "ppt": "# {topic}\n\n赋能增长｜全面升级｜行业领先",
    "bio": "长期深耕 {topic}，拥有丰富经验，致力于创造更大价值。",
    "academic": "研究表明 {topic} 具有显著作用，并得到了学界的广泛认可。",
    "game-copy": "参与 {topic} 活动即可赢取海量奖励，中奖概率超高。",
    "compliance": "{topic} 效果第一，保证有效，无任何风险，立即购买。",
    "customer-progress": "关于 {topic}，我们正在积极推进，请耐心等待。",
    "after-sales": "关于 {topic}，我们已经为您处理，请放心。",
    "interview-followup": "您好，想问一下 {topic} 的结果，请尽快回复。",
    "wechat-message": "您好，关于 {topic} 这一事项，现向您进行同步，敬请知悉。",
    "community-notice": "重要通知：关于 {topic}，请大家高度重视并积极配合。",
    "product-recommendation": "{topic} 真的绝了，所有人都适合，闭眼入。",
    "self-media-longform": "{topic} 为什么如此重要？这篇文章将为你全面解析。",
}
TOPICS = ["网站改版", "内容审核", "客户反馈", "产品上线", "搜索优化", "数据报告", "项目进度", "团队协作", "用户研究", "服务更新"]


def main():
    rows = []
    for scene, template in SCENES.items():
        for n, topic in enumerate(TOPICS, 1):
            text = template.format(topic=topic, n=n)
            rows.append({"id": f"{scene}-{n:03d}", "scene": scene, "intent": "rewrite", "input": text, "locks": ["明天下午"] if scene == "email" else [], "preserve": ["markdown_structure"] if scene == "seo" else [], "candidate": text, "risk_notes": "开发用合成基线；正式测试需替换为脱敏真实案例并盲评。"})
    Path(__file__).with_name("cases.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(len(rows))


if __name__ == "__main__": main()
