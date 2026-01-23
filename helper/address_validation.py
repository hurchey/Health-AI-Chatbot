import os
import re
from typing import Any, Dict, List, Optional

import requests

GOOGLE_URL = "https://addressvalidation.googleapis.com/v1:validateAddress"
ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")


def _extract_input_zip(raw: str) -> Optional[str]:
    m = ZIP_RE.search(raw or "")
    return m.group(1) if m else None


def _get_component(components: List[Dict[str, Any]], component_type: str) -> Optional[Dict[str, Any]]:
    for c in components or []:
        if c.get("componentType") == component_type:
            return c
    return None


def validate_address_line(address_line: str, region_code: str = "US", timeout_s: int = 15) -> dict:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {
            "is_valid": False,
            "needs_confirmation": False,
            "formatted": None,
            "place_id": None,
            "missing_fields": ["google_api_key_missing"],
            "message": "Missing GOOGLE_MAPS_API_KEY",
        }

    raw = (address_line or "").strip()
    input_zip = _extract_input_zip(raw)

    body = {"address": {"regionCode": region_code, "addressLines": [raw]}}

    try:
        resp = requests.post(
            GOOGLE_URL,
            params={"key": api_key},
            json=body,
            timeout=timeout_s,
        )
        data = resp.json()
    except Exception:
        return {
            "is_valid": False,
            "needs_confirmation": False,
            "formatted": None,
            "place_id": None,
            "missing_fields": ["api_request"],
            "message": "Address validation request failed.",
        }

    if resp.status_code != 200:
        return {
            "is_valid": False,
            "needs_confirmation": False,
            "formatted": None,
            "place_id": None,
            "missing_fields": ["google_error"],
            "message": "Google address validation returned an error (check API key / billing / API enabled).",
        }

    result = (data or {}).get("result", {}) or {}
    verdict = result.get("verdict", {}) or {}
    addr = result.get("address", {}) or {}
    geocode = result.get("geocode", {}) or {}

    formatted = addr.get("formattedAddress")
    place_id = (geocode or {}).get("placeId")
    missing_fields = addr.get("missingComponentTypes") or []
    components = addr.get("addressComponents") or []

    next_action = verdict.get("possibleNextAction")  
    granularity = verdict.get("validationGranularity")
    address_complete = bool(verdict.get("addressComplete"))

    postal_comp = _get_component(components, "postal_code")
    output_zip = None
    if postal_comp and isinstance(postal_comp.get("componentName"), dict):
        output_zip = postal_comp["componentName"].get("text")
    if input_zip and output_zip:
        out5 = output_zip.strip()[:5]
        if out5.isdigit() and out5 != input_zip:
            return {
                "is_valid": False,
                "needs_confirmation": False,
                "formatted": formatted,
                "place_id": place_id,
                "missing_fields": missing_fields,
                "message": "That ZIP code doesn't match the street address. Please re-enter the full address.",
            }

    if next_action == "FIX":
        return {
            "is_valid": False,
            "needs_confirmation": False,
            "formatted": formatted,
            "place_id": place_id,
            "missing_fields": missing_fields,
            "message": "That address couldn't be validated. Please re-enter it (street, city, state, ZIP).",
        }

    if next_action in {"CONFIRM", "CONFIRM_ADD_SUBPREMISES"} or granularity in {"ROUTE", "PREMISE_PROXIMITY"}:
        return {
            "is_valid": False,
            "needs_confirmation": True,
            "formatted": formatted,
            "place_id": place_id,
            "missing_fields": missing_fields,
            "message": "I found a close match. Please confirm it's exactly correct.",
        }

    is_valid = address_complete and granularity in {"PREMISE", "SUB_PREMISE"}
    return {
        "is_valid": bool(is_valid),
        "needs_confirmation": False if is_valid else True,
        "formatted": formatted,
        "place_id": place_id,
        "missing_fields": missing_fields,
        "message": "OK" if is_valid else "I found a close match. Please confirm it's exactly correct.",
    }
