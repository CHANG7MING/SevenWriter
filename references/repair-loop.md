# Repair Loop

## Failure tags

- `faithfulness.entity|number|modality|causality|fabrication`
- `scene.intent|audience|format|length|cta`
- `naturalness.template|contrast|elevation|rhythm|forced_colloquial`
- `density.repetition|vague|padding|overcompression`
- `style.voice|punctuation|register|ending`
- `document.structure|link|table|code|cross_section`

## 循环

1. 以当前 best-so-far 为输入，不从原文重新抽样。
2. 选择最高风险的 1–3 个 tags；`faithfulness.*` 永远优先。
3. 写出局部修复指令和不可触碰项。
4. 生成一个修复候选。
5. 重新跑硬门槛与受影响维度；抽查未修改区域。
6. 仅在有实质改善且复杂度没有不必要增加时保留。
7. 达到质量门槛、两轮无改善或三轮上限时停止。

## 停止条件

- `pass`：硬门槛全过，关键维度无明显缺陷。
- `stable`：改动收益小于 2 分，保留更简单版本。
- `blocked`：缺事实、目标冲突或需要用户选择；列出最小问题。
- `reject`：候选破坏内容契约。

不要用“再写一遍”作为修复指令。指出位置、问题、目标和边界。
