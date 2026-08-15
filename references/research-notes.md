# 外部研究转化记录

只记录可迁移的设计判断，不复制规则、提示词或代码。

- 文本风格迁移研究通常同时评价风格强度、内容保留和流畅度；SevenWriter 将其扩展为事实保真、场景适配、自然度、信息密度、文风匹配、可读性与模式风险。
- 自动指标与人工判断存在偏差；Benchmark 要求硬检查、明确 rubric 和盲评分开报告。
- FaithEval 一类评测强调不可回答、冲突和反事实上下文；SevenWriter 用 `UNKNOWN`、情态检查和硬性内容契约阻止“补全”未知事实。
- Word 的文本可能跨多个 run/node；SevenWriter 以段落 ID 写入副本，报告格式风险，不承诺文本框或复杂域无损。

来源：

- https://aclanthology.org/N19-1049/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12191983/
- https://github.com/SalesforceAIResearch/FaithEval
- https://pypi.org/project/python-docx-replace/
