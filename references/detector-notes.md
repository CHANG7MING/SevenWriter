# AI 文本检测器：公开机制与使用边界

更新基线：2026-08-12。产品机制会变化；在引用当前能力或价格前重新核对官网。

## 共识

检测器通常基于语言统计、分类模型或深度学习，对“文本更像哪一类训练样本”给出概率判断。它们不能证明作者身份、创作过程或是否使用过辅助编辑。短文本、混合人机文本、改写文本、特定体裁和语言迁移会改变误差。

SevenWriter 不调用检测器，不优化检测分，不承诺绕过检测。若用户提供分数，将其记录在独立的 `external_signals` 中，不能进入质量总分或覆盖人工证据。

## OpenAI AI Text Classifier

- OpenAI 于 2023-07-20 因准确率低下线该工具。
- 官方公布的英文 challenge set 中，只有 26% 的 AI 文本被判为“likely AI-written”，人类文本误报率为 9%。
- 官方说明短文本不可靠，要求至少 1,000 字符；英文外表现更差，且编辑可规避。

结论：只作为历史案例，不能作为 SevenWriter 集成目标。

## GPTZero

- 早期以 perplexity 和 burstiness 等作为解释信号；其官方资料说明自 2023 年秋起已迁移到深度学习架构，不再直接用这两项做最终检测。
- 官方也承认短文本、编辑文本和混合文本更难判断，且没有检测器能达到 100% 准确。

结论：不要把“增加随机性/爆发度”变成写作规则；这会诱发无意义改写。

## Originality.AI

- 官方描述为持续更新的分类模型，并公开不同模型、数据集、阈值、假阳性与假阴性指标。
- 官方建议至少约 100 词；短文本、公式化体裁、公共领域文本、学术文本和 AI 辅助编辑可能产生误判。
- 厂商自报准确率必须结合版本、数据集、语言和阈值理解，不能跨场景外推。

## ZeroGPT

- 公开营销资料通常提及语言模型/统计分析和专有算法，但缺少足以复现、审计训练数据与阈值的完整技术披露。
- 输出百分比不应被解释为“有多少文字由 AI 写成”的可验证比例。

## Writer AI Content Detector

- Writer 曾提供公开检测器，公开说明主要是产品级描述，缺少可独立复现的完整模型与数据细节；其产品可用性与入口会变化。
- 不要把历史页面或第三方截图当作当前能力证据。

## 已知局限与伦理风险

- 误报/漏报随模型、语言、体裁、长度和编辑方式漂移。
- 研究发现部分检测器会对非英语母语者写作产生系统性偏差；相关证据主要来自英文，不应未经验证直接量化到中文，但足以要求谨慎。
- 高风险判断应结合草稿、版本历史、来源、引用核验与作者解释，不能只凭单一分数。

## 参考来源

- OpenAI, “New AI classifier for indicating AI-written text” (2023，含下线说明)：https://openai.com/index/new-ai-classifier-for-indicating-ai-written-text/
- GPTZero, “How do I interpret burstiness or perplexity?”：https://support.gptzero.me/articles/9585228410-how-do-i-interpret-burstiness-or-perplexity
- GPTZero, “How Do AI Detectors Work?”：https://gptzero.me/news/how-ai-detectors-work/
- Originality.AI, false-positive guidance：https://help.originality.ai/en/article/most-common-reasons-for-false-positives-with-originality-1sf6ykc/
- Liang et al., “GPT detectors are biased against non-native English writers”：https://arxiv.org/abs/2304.02819

厂商页面属于第一方产品声明，不等于独立验证。ZeroGPT 与 Writer 因公开可审计资料有限，只记录其边界，不推断未披露机制。
