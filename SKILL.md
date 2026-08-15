---
name: seven-writer
description: 面向 AI Agent 的中文写作、创作、改写、诊断、润色与文风控制 Skill。适用于邮件和即时消息、客户沟通、社群通知、SEO/GEO、网站与产品文案、博客、公众号文章、朋友圈文案、自媒体、社交帖子、小红书、短视频口播、播客、周报、个人简介、PPT、演讲稿、Markdown/Word 长文、协议、学术及游戏文案；支持基础纠错、去 AI 味、正式写作、可读性优化、一致性检查、地道表达和适度口语化，并可检查版权商标、广告投放及受监管主张等合规风险。在保持事实、数字、专名、引用、链接、关键词和文档结构的前提下，提高场景适配、自然度、信息密度与文风匹配。不以规避 AI 检测器为目标，也不以语言优化代替法律、学术或行业专业审查。
---

# SevenWriter

把任务当作写作质量控制，而不是同义词替换或检测器降分。

## 核心原则

1. 先确认任务意图：`analyze`、`rewrite` 或 `create`。
2. 先建立内容契约，再改字。事实保真优先于自然度；场景目标优先于通用“人味”。
3. “像人”表示符合真实场景和作者习惯，不表示强行口语化、制造错别字或虚构亲历。
4. 规则命中只产生证据与警告；结合上下文判断，不机械删词。
5. 使用检测器结果时只把它当外部弱信号，不当真值、验收门槛或优化目标。
6. 未经用户要求，不展示冗长内部候选和评分过程；交付成稿，并简述重要改动与风险。

## 九层工作流

### 1. 路由意图与场景

识别意图、受众、渠道、目的、语体、长度、输出格式。按需读取一个或多个场景文件：

先分开判断“输入来源”和“优化目标”。用户只给 URL 时，将其视为网页来源：读取 HTML、提取正文与结构，再按用户实际目的创作/改写；不得自动推断 SEO 或 GEO。只有用户明确提出 SEO、搜索引擎优化、GEO、生成式引擎/答案引擎优化时，才加载对应 profile。

- 通用与长文：`profiles/general.md`、`profiles/longform.md`
- SEO/GEO：`profiles/seo.md`、`profiles/geo.md`
- 小红书与短视频：`profiles/xiaohongshu.md`、`profiles/short-video.md`
- 邮件：`profiles/email.md`
- 演讲：`profiles/speech.md`
- 通用社交、朋友圈与网站产品：`profiles/social.md`、`profiles/website.md`
- 客户进度、售后退款物流、面试跟进、微信短消息、社群通知、产品推荐、自媒体长文：`profiles/communication.md`
- 播客、周报、PPT、个人简介、公众号文章与博客：`profiles/editorial.md`
- 协议、学术、游戏文案及版权/商标/广告/受监管主张审查：`profiles/professional.md`、`profiles/compliance.md`

将基础纠错、去 AI 味、正式写作、可读性优化、一致性检查、地道表达和俚语/流行语视为可叠加能力，而不是互斥场景。先选择实际载体与读者，再叠加能力规则。俚语和流行语必须符合人物、品牌、年代、地区和渠道，不得为了“真人感”强行添加。

### 2. 建立内容契约

读取 `references/faithfulness.md`。列出 LOCK、SOFT LOCK、PRESERVE、可改项和未知项。默认锁定事实、数字、日期、人名、产品名、专业术语、URL、引用归属；不得把推测升级为事实。

### 3. 诊断写作信号

读取 `references/ai-patterns.md` 与 `references/writing-principles.md`。区分：

- `FAIL`：可由证据确认的问题，如改坏事实、虚构经历、空占位符。
- `WARN`：需上下文判断的模式，如机械转折、空泛升华、段落过度对称。
- `INFO`：统计特征，如句长分布、重复连接词。

可运行：

```shell
python scripts/sevenwriter.py analyze input.md --profile seo
```

网页输入先运行：

```shell
python scripts/sevenwriter.py fetch-url https://example.com --output page.json
```

根据 `page.json` 的正文和结构完成创作；网页来源本身不触发 SEO/GEO。

脚本只辅助定位；完整通读决定是否修改。

### 4. 应用场景配置

只加载相关 profile。场景约束可覆盖通用偏好，但不能覆盖内容契约。例如 SEO 保留搜索意图与关键词；小红书不得凭空编造“亲测”；口播优先朗读节奏。

### 5. 匹配作者文风

若用户提供样文，读取 `references/style-analysis.md`，并运行 `python scripts/sevenwriter.py style ...` 提取句长与段长、标点、第一人称、连接词和结尾习惯。只模仿可观察的风格特征，不复制独特措辞，不凭风格样本引入新事实。无样文时使用场景默认，不假装“像用户本人”。

### 6. 生成最少必要候选

按风险选择候选数量：

- 短邮件/消息：1 个主稿；有明显权衡时再给 1 个备选。
- 一般改写：`minimal` 与 `natural` 两种内部候选。
- SEO/GEO/演讲/长文：可加入 `scene` 或 `structural` 候选。

候选必须共享同一内容契约。不要用随机扰动、错别字或无意义口语词制造差异。

### 7. 多维评分

读取 `references/scoring-rubric.md`。先执行硬门槛，再评估：事实保真 25、场景适配 20、自然度 20、信息密度 15、文风匹配 10、可读性 5、模式风险 5。每一项必须同时报告原始分、加权分、得分理由、扣分理由、证据和提升条件；不得只给数字。检测器分数不计入 100 分。

需要“先校核、再创作、后独立复核”时，读取 `references/editorial-team.md` 并启用三人编辑部：资料校核席先建立证据包，场景主笔席是唯一正文写入者，独立终审席用新上下文复核。SEO/GEO、学术、协议、合规、受监管主张和长文档默认建议启用；短消息和低风险轻改使用最小必要流程。三席分别给分和解释，不得用平均分掩盖否决、证据不足或具体修改项。

需要比较多个现成候选时，读取 `references/jury-design.md`，使用兼容的候选盲评模式。不得使用外部材料中的人物姓名、人设、原评语、提示词或调度配置。

可运行：

```shell
python scripts/sevenwriter.py score candidate.md --source source.md --profile seo
python scripts/sevenwriter.py compare baseline.md candidate.md --source source.md --profile seo
```

需要自动闭环时，使用 `prepare` 交给当前 Agent 执行，或使用 `run --team` 连接外部命令/OpenAI-compatible 模型并启用三人编辑部。具体见 `references/host-integration.md`。

### 8. 定向修复

读取 `references/repair-loop.md`。从 best-so-far 修复最高优先级 failure tags；一次只修 1–3 类问题。修复后重新检查内容契约和相关维度。无实质改善、破坏事实或仅降低检测分时丢弃。默认最多 3 轮。

### 9. 文档模式

处理 Markdown/Word 长文时读取 `references/document-mode.md`。先建立文档地图与全局风格，再逐节处理，最后做跨节一致性检查。Markdown 使用 `map`/`merge-md`；Word 使用 `docx-extract`/`docx-apply` 按段落 ID 写入新副本。复杂文本框、域和跨 run 样式必须报告限制，不覆盖原文件。

## 输出约定

- `analyze`：给出按严重度排序的证据、位置、原因与建议；不自动改稿。
- `rewrite/create`：先给最终成稿，再提供完整评分；从零创作也必须接受同一套事实、场景、自然度、密度、文风和可读性评审。
- 文件任务：写入新文件，除非用户明确授权覆盖；保持原扩展名与结构。
- 无足够事实时标注 `[待确认]` 或提出必要问题，不补写看似合理的细节。
- 启用自动闭环时同时生成：`final.md`（成稿副本）、`review-report.md`（逐项评分理由、三人独立意见、合并分、位置化修改表、保留项、淘汰理由和发布/发送建议）、`revision-plan.json`（机器可读修改清单）与 `run.json`（完整记录）。修改表至少包含优先级、位置、当前内容、问题、原因、建议改法、参考改文、验证方式和人工确认状态。不得只给总分而隐藏证据。

## 资源导航

- 写作模式：`references/ai-patterns.md`
- 写作原则：`references/writing-principles.md`
- 保真契约：`references/faithfulness.md`
- 检测器机制与边界：`references/detector-notes.md`
- 评分：`references/scoring-rubric.md`
- 修复：`references/repair-loop.md`
- Benchmark：`references/benchmark-design.md`
- 文档：`references/document-mode.md`
- 参考吸收边界：`references/reference-boundaries.md`
- 样文风格：`references/style-analysis.md`
- 宿主与生成后端：`references/host-integration.md`
- 外部研究转化：`references/research-notes.md`
- GPTZero 理念转化：`references/gptzero-inspired-signals.md`
- 三人评审机构与候选盲评：`references/jury-design.md`
- 三人编辑部的证据、主笔与独立终审：`references/editorial-team.md`
- 统一评分、修改表与发布清单：`references/review-output-contract.md`
- 学术选刊、分区指标与投稿准备度：`references/academic-journal-readiness.md`

## 最小运行要求

Python 3.9+，仅使用标准库。脚本支持当前 Agent job、外部命令和 OpenAI-compatible 生成后端；未配置后端时只准备任务，不伪造候选。
