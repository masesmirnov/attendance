from __future__ import annotations

import re
from typing import Any


COL_RE = re.compile(r"^[A-Z]{1,3}$")
SHEET_ID_RE = re.compile(r"^[a-zA-Z0-9\-_]{20,}$")
SHEET_ID_FROM_URL_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9\-_]+)")


def strip_or_none(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def normalize_column(col: str) -> str:
    return col.strip().upper()


def is_valid_column(col: str) -> bool:
    return bool(COL_RE.fullmatch(normalize_column(col)))


def extract_sheet_id(text: str) -> str | None:
    text = text.strip()
    m = SHEET_ID_FROM_URL_RE.search(text)
    if m:
        cand = m.group(1).strip()
        return cand if SHEET_ID_RE.fullmatch(cand) else None

    return text if SHEET_ID_RE.fullmatch(text) else None
