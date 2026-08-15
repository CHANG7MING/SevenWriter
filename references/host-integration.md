# 宿主集成

SevenWriter 的基础协议是整个目录、`SKILL.md` 和 Python 3.9+。

## 通用安装

```shell
python scripts/sevenwriter.py install --target <宿主的 skills/seven-writer 目录>
```

安装命令只接受一个尚未放置内容的目录；检测到已有文件便停止，由使用者决定合并方式。SevenWriter 不猜测宿主的本地目录：先查看该宿主当前配置，再把确认后的路径传给 `--target`。这项约束用于防止误覆盖，也让同一份 Skill 可以迁移到不同 Agent 环境。

## 生成后端

- 当前 Agent：运行 `prepare` 得到 `job.json`，Agent 依次完成其中 prompts，再用 `score/compare` 评审。
- 外部命令：`run --backend command --command "<读取 stdin、向 stdout 输出正文的命令>"`。
- OpenAI-compatible：`run --backend openai-compatible --endpoint <chat completions URL> --model <model>`；密钥默认读取 `SEVENWRITER_API_KEY`。

端点只需要兼容 Chat Completions 的 `choices[0].message.content`。SevenWriter 不保存 API key。

## 网页来源

用户提供 HTML 地址时先运行 `fetch-url`，或使用宿主浏览器/网页读取工具获取可见正文、标题、描述、标题层级和链接。将“读取网页”与“SEO/GEO 优化”分开：只有用户明确提出对应目标时才加载 SEO/GEO profile。

## 冒烟检查

复制后运行：

```shell
python scripts/sevenwriter.py analyze README.md --profile general
python scripts/sevenwriter.py benchmark benchmarks/cases.jsonl
```
