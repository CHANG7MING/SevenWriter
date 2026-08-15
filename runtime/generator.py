from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.request
from dataclasses import dataclass


STRATEGIES = {
    "minimal": "只修明确问题，尽量保留原句序、结构与措辞。",
    "natural": "允许调整句式、段落和连接，使表达自然具体，但不改变信息。",
    "structural": "允许重排叙述和标题，以读者理解为主；严格服从内容契约。",
    "scene": "优先满足所选场景 profile，并保持事实、关键词和格式。",
    "style": "匹配给定样文的统计风格特征，不复制独特句子。",
    "repair": "只修复列出的 failure tags，不重写已经通过的部分。",
}


@dataclass
class GenerationRequest:
    source: str
    task: str
    scene: str
    strategy: str
    contract: dict
    style: dict | None = None
    repair_tags: list[dict] | None = None


def build_prompt(req: GenerationRequest) -> str:
    # Keep command/API backends aligned with the same scene requirements used by review.
    from runtime.jury import SCENE_BRIEFS
    scene_requirements = SCENE_BRIEFS.get(req.scene, SCENE_BRIEFS["general"])
    payload = {
        "task": req.task,
        "scene": req.scene,
        "strategy": req.strategy,
        "strategy_instruction": STRATEGIES[req.strategy],
        "scene_requirements": scene_requirements,
        "content_contract": req.contract,
        "style_profile": req.style,
        "repair_tags": req.repair_tags or [],
        "source": req.source,
    }
    return "你正在执行 SevenWriter 写作任务。只输出候选正文，不解释过程。不得虚构材料中没有的事实。\n" + json.dumps(payload, ensure_ascii=False, indent=2)


class Generator:
    def generate(self, request: GenerationRequest) -> str:
        return self.generate_prompt(build_prompt(request))

    def generate_prompt(self, prompt: str) -> str:
        raise NotImplementedError


class CommandGenerator(Generator):
    def __init__(self, command: str):
        self.command = command

    def generate_prompt(self, prompt: str) -> str:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(shlex.split(self.command, posix=os.name != "nt"), input=prompt, text=True, encoding="utf-8", errors="strict", capture_output=True, check=True, env=env)
        if not result.stdout.strip():
            raise RuntimeError("生成命令没有返回正文")
        return result.stdout.strip()


class OpenAICompatibleGenerator(Generator):
    def __init__(self, endpoint: str, model: str, api_key: str | None = None):
        self.endpoint, self.model, self.api_key = endpoint, model, api_key

    def generate_prompt(self, prompt: str) -> str:
        body = json.dumps({"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
