from __future__ import annotations

import json
import re
import urllib.request
from html.parser import HTMLParser


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.description, self.headings, self.links, self.parts = "", "", [], [], []
        self._skip = 0; self._capture_title = False; self._heading = None; self._buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript", "svg"}: self._skip += 1
        if tag == "title": self._capture_title = True; self._buffer = []
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}: self._heading = tag; self._buffer = []
        if tag == "meta" and attrs.get("name", "").lower() == "description": self.description = attrs.get("content", "")
        if tag == "a" and attrs.get("href"): self.links.append(attrs["href"])
        if tag in {"p", "li", "blockquote", "br", "section", "article"}: self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self._skip: self._skip -= 1
        if tag == "title" and self._capture_title: self.title = "".join(self._buffer).strip(); self._capture_title = False; self._buffer = []
        if self._heading == tag:
            text = "".join(self._buffer).strip()
            if text: self.headings.append({"level": int(tag[1]), "text": text})
            self._heading = None; self._buffer = []

    def handle_data(self, data):
        if self._skip: return
        if self._capture_title or self._heading: self._buffer.append(data)
        self.parts.append(data)


def fetch_page(url: str, timeout: int = 30) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "SevenWriter/0.2 (+local writing assistant)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(); content_type = response.headers.get_content_charset() or "utf-8"; final_url = response.geturl()
    html = raw.decode(content_type, errors="replace")
    parser = PageParser(); parser.feed(html)
    text = re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", "".join(parser.parts))).strip()
    return {"schema": "sevenwriter.webpage.v1", "requested_url": url, "final_url": final_url, "title": parser.title, "description": parser.description, "headings": parser.headings, "links": parser.links, "text": text, "notice": "网页来源不等于 SEO/GEO 任务；只有用户明确要求时才加载对应优化 profile。"}
