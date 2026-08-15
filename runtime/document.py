from __future__ import annotations

import re


def map_markdown(text: str) -> dict:
    sections = split_markdown(text)
    return {"lines": len(text.splitlines()), "sections": sections, "urls": re.findall(r"https?://[^\s)\]>]+", text), "fences_balanced": len(re.findall(r"^```", text, re.M)) % 2 == 0}


def split_markdown(text: str) -> list[dict]:
    lines = text.splitlines(keepends=True)
    sections, current, heading, level, start = [], [], "document", 0, 1
    in_code = False
    for number, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        match = None if in_code else re.match(r"^(#{1,6})\s+(.+)", line)
        if match and current:
            sections.append({"id": f"s{len(sections)+1}", "heading": heading, "level": level, "start_line": start, "end_line": number - 1, "text": "".join(current)})
            current, heading, level, start = [], match.group(2).strip(), len(match.group(1)), number
        elif match:
            heading, level, start = match.group(2).strip(), len(match.group(1)), number
        current.append(line)
    if current:
        sections.append({"id": f"s{len(sections)+1}", "heading": heading, "level": level, "start_line": start, "end_line": len(lines), "text": "".join(current)})
    return sections


def merge_sections(original: str, replacements: dict[str, str]) -> str:
    return "".join(replacements.get(section["id"], section["text"]) for section in split_markdown(original))
