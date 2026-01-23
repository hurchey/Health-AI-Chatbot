import json
from pathlib import Path
from typing import Any, Dict

DATA_DIR = Path("data")
LATEST_STATE_PATH = DATA_DIR / "latest_session.json"


def save_latest_state(state_dict: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_STATE_PATH.write_text(json.dumps(state_dict, indent=2), encoding="utf-8")
