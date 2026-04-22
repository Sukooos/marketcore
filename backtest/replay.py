from __future__ import annotations

import json
import math
from typing import Any


def _validate_finite_numbers(payload: Any) -> None:
    if isinstance(payload, float) and not math.isfinite(payload):
        raise ValueError("non-finite numeric value in payload")
    if isinstance(payload, tuple):
        raise ValueError("non-JSON-native container in payload: tuple")
    if isinstance(payload, dict):
        for value in payload.values():
            _validate_finite_numbers(value)
    elif isinstance(payload, list):
        for value in payload:
            _validate_finite_numbers(value)


def _canonical_payload_json(payload: dict[str, Any]) -> str:
    _validate_finite_numbers(payload)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def events_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _canonical_payload_json(left) == _canonical_payload_json(right)
