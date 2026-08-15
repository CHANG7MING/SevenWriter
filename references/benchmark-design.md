# Benchmark 设计

目标是验证 SevenWriter 的版本变化是否真正改善写作，不证明文本由谁创作。

## 数据集

项目自带每个一级场景 10 个合成回归案例，覆盖 SEO、GEO、小红书、短视频、邮件、演讲、网站、长文、播客、周报、协议、PPT、个人简介、学术、游戏、合规及中文沟通子场景。它们用于验证程序、路由、规则和版本回归，不代表真实质量。正式验收还需加入脱敏真实案例，并覆盖不同约束强度、创作、诊断和重写任务。测试集不进入规则开发。

每条 JSONL：`id`、`scene`、`intent`、`input`、`constraints`、`locks`、`style_reference`、`rubric_overrides`、`risk_notes`。不得存入未脱敏隐私或受限内容。

## 评测顺序

1. 自动硬检查：锁定字符串、数字、URL、Markdown 结构、长度。
2. 基于证据的 rubric 评审：事实、场景、自然、密度、风格、可读性、模式风险。
3. 人工盲选：隐藏版本标签，至少 2 名评审；冲突时保留分歧。
4. 统计分场景结果，不只看总体均值；报告失败率和置信区间。
5. 外部 detector 可选、单列、不可决定 keep/discard。

## 版本门槛

- LOCK 失败率不得上升。
- 任一关键场景不得出现显著退化。
- 综合偏好提升但复杂度明显上升时，记录成本并要求足够收益。
- 新版本先在开发集改进，再一次性查看保留测试集。

## 实验日志

使用 `benchmarks/results.tsv`：`version, case_id, status, total, faithfulness, scene_fit, naturalness, density, style, notes`。状态为 `keep`、`discard`、`reject`。所有版本在相同案例、相同 rubric 和相同评审设置下比较。
