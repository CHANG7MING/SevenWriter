from __future__ import annotations

import json
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
TEXT_PARTS = ("word/document.xml", "word/header1.xml", "word/footer1.xml", "word/footnotes.xml", "word/endnotes.xml", "word/comments.xml")


def extract_docx(path: Path) -> dict:
    paragraphs = []
    with zipfile.ZipFile(path) as archive:
        for part in TEXT_PARTS:
            if part not in archive.namelist():
                continue
            root = ET.fromstring(archive.read(part))
            for index, paragraph in enumerate(root.iter(W + "p")):
                nodes = list(paragraph.iter(W + "t"))
                text = "".join(node.text or "" for node in nodes)
                if text.strip():
                    paragraphs.append({"id": f"{part}#p{index}", "part": part, "index": index, "text": text, "runs": len(nodes)})
    return {"schema": "sevenwriter.docx-map.v1", "source": str(path), "paragraphs": paragraphs, "limitations": ["文本框、SmartArt、域代码和嵌入对象可能不在普通段落中", "整段替换会沿用首个文本节点的字符样式"]}


def apply_docx_replacements(source: Path, replacements_file: Path, output: Path) -> dict:
    replacements_data = json.loads(replacements_file.read_text(encoding="utf-8"))
    replacements = replacements_data.get("replacements", replacements_data)
    if isinstance(replacements, list):
        replacements = {item["id"]: item["text"] for item in replacements}
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    changed, missing = [], set(replacements)
    with tempfile.TemporaryDirectory(prefix="sevenwriter-docx-") as temp:
        temp_path = Path(temp)
        with zipfile.ZipFile(source) as archive:
            archive.extractall(temp_path)
        for part in TEXT_PARTS:
            file = temp_path / part
            if not file.exists():
                continue
            tree = ET.parse(file)
            root = tree.getroot()
            for index, paragraph in enumerate(root.iter(W + "p")):
                key = f"{part}#p{index}"
                if key not in replacements:
                    continue
                nodes = list(paragraph.iter(W + "t"))
                if not nodes:
                    continue
                nodes[0].text = str(replacements[key])
                for node in nodes[1:]:
                    node.text = ""
                changed.append(key); missing.discard(key)
            tree.write(file, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in temp_path.rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(temp_path).as_posix())
    return {"output": str(output), "changed": changed, "missing": sorted(missing), "source_preserved": str(source)}
