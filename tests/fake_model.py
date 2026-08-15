from __future__ import annotations

import json
import sys

prompt = sys.stdin.read()
payload = json.loads(prompt[prompt.index("{"):])
source = payload["source"]
text = source.replace("综上所述，", "").replace("感谢您的理解与支持，如有任何问题请随时联系我们。", "有新进展我会及时同步。")
print(text)
