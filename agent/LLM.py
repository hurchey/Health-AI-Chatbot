from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

from openai import OpenAI


def _extract_json_object(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return {}


class LLMClient:
    def __init__(self) -> None:
        self.client = OpenAI()
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def chat_and_extract(
        self,
        step_name: str,
        missing_fields: List[str],
        user_message: str,
        state_public: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        system = (
            "You are a friendly medical intake representative in a terminal.\n"
            "Collect required info step-by-step and keep the user moving.\n"
            "- Ask ONE question at a time.\n"
            "- If user asks a question, answer briefly then continue.\n"
            "- Do NOT ask for insurance ID/member ID (payer name only).\n"
            "- Do NOT say 'press enter' or 'let's move to the next step'.\n"
            "Special: if step_name is 'qa', ask if they have any questions (yes/no).\n"
            "Output JSON ONLY: {\"assistant_message\":\"...\",\"updates\":{...}}.\n"
            "Never invent values."
        )

        schema_hint = {
            "patient": {"full_name": "string", "date_of_birth": "string"},
            "insurance": {"payer_name": "string"},
            "medical": {"chief_complaint": "string"},
            "demographics": {"raw_address_line": "string"},
        }

        user = (
            f"step_name: {step_name}\n"
            f"missing_fields: {missing_fields}\n"
            f"state: {json.dumps(state_public, ensure_ascii=False)}\n"
            f"schema_for_updates: {json.dumps(schema_hint)}\n"
            f"user_message: {user_message}\n"
        )

        resp = self.client.responses.create(
            model=self.model,
            input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )

        obj = _extract_json_object(resp.output_text)
        assistant_message = (obj.get("assistant_message") or "").strip()
        updates = obj.get("updates") or {}
        if not isinstance(updates, dict):
            updates = {}
        if not assistant_message:
            assistant_message = "Got it."
        return assistant_message, updates

    def answer_user_question(self, question: str, state_public: Dict[str, Any]) -> str:
        system = (
            "You are a helpful intake representative.\n"
            "Answer briefly and clearly.\n"
            "Do NOT invent facts.\n"
            "Do NOT diagnose.\n"
        )
        user = f"state: {json.dumps(state_public, ensure_ascii=False)}\nquestion: {question}\n"
        resp = self.client.responses.create(
            model=self.model,
            input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return (resp.output_text or "").strip() or "I'm not sure — could you rephrase that?"
