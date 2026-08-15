from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from runtime.router import SCENE_HINTS, SUBSCENE_HINTS

REQUIRED = {"id", "scene", "intent", "draft_state", "brief", "input", "locks", "must_find", "must_not_introduce", "acceptance"}
INTENTS = {"create", "analyze", "light_rewrite", "deep_rewrite"}
STATES = {"excellent", "ordinary", "problematic", "protected"}


def main() -> int:
    path = Path(__file__).with_name("cases.jsonl")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    errors = []
    ids = set()
    for row in rows:
        missing = REQUIRED - row.keys()
        if missing: errors.append(f"{row.get('id')}: missing {sorted(missing)}")
        if row.get("id") in ids: errors.append(f"duplicate id: {row.get('id')}")
        ids.add(row.get("id"))
        if row.get("intent") not in INTENTS: errors.append(f"{row.get('id')}: invalid intent")
        if row.get("draft_state") not in STATES: errors.append(f"{row.get('id')}: invalid draft_state")
        if not row.get("acceptance"): errors.append(f"{row.get('id')}: acceptance is empty")
    expected = set(SCENE_HINTS) | set(SUBSCENE_HINTS)
    covered = {row["scene"] for row in rows}
    missing_scenes = expected - covered
    if missing_scenes: errors.append(f"missing scenes: {sorted(missing_scenes)}")
    summary = {"cases": len(rows), "scenes": len(covered), "intents": Counter(r["intent"] for r in rows), "states": Counter(r["draft_state"] for r in rows), "errors": errors}
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=dict))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
