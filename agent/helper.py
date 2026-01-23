from __future__ import annotations

import re
from typing import Optional


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def yes_no(s: str) -> Optional[bool]:
    t = (s or "").strip().lower()

    if t.startswith(("no", "nah", "nope")) or t in {"none"}:
        return False

    if t.startswith(("yes", "yep", "yeah", "y")) or t in {"ok", "okay", "sure"}:
        return True

    return None


def first_name(full_name: Optional[str]) -> str:
    if not full_name:
        return "there"
    parts = full_name.strip().split()
    return parts[0] if parts else "there"
