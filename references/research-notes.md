# 外部研究转化记录

只记录可迁移的设计判断，不复制规则、提示词或代码。

- Mir 等人的文本风格迁移评测将风格强度、内容保留和自然度分开，并指出三者存在权衡；SevenWriter 因此先分别报告三项基础分，再叠加场景维度，不能只看综合分。
- TSTBench 同时使用统一的自动指标与人工评价，并对风格强度、内容保留、流畅度和总体质量采用明确的 1–5 分人工量表；SevenWriter 借鉴“自动检查 + 人工语义评审”的分层方式，但不复制其数据集、实现或指标组合。
- FaithEval 一类评测强调不可回答、冲突和反事实上下文；SevenWriter 用 `UNKNOWN`、情态检查和硬性内容契约阻止“补全”未知事实。
- Word 的文本可能跨多个 run/node；SevenWriter 以段落 ID 写入副本，报告格式风险，不承诺文本框或复杂域无损。

来源：

- https://aclanthology.org/N19-1049/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12191983/
- https://github.com/SalesforceAIResearch/FaithEval
- https://pypi.org/project/python-docx-replace/
