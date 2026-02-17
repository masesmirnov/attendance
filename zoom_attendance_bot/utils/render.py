from __future__ import annotations

import html
import json
from typing import Any


def as_html_json_codeblock(obj: Any) -> str:
    txt = json.dumps(obj, ensure_ascii=False, indent=2)
    return f"<pre><code>{html.escape(txt)}</code></pre>"
