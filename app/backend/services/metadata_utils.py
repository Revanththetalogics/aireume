"""
Utility for safely parsing tenant metadata_json field.

The metadata_json column may be:
- A Python dict (SQLAlchemy JSON column auto-deserialization)
- A JSON string containing a dict: '{"key": "value"}'
- A double-encoded JSON string: '"{\\"key\\": \\"value\\"}"'
- A plain quoted string: '"something"'
- None or empty string

This helper guarantees a dict is always returned.
"""
import json


def safe_parse_metadata(raw) -> dict:
    """
    Safely parse tenant.metadata_json into a dict, handling all edge cases.
    Always returns a dict, never raises.
    """
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        # Handle double-encoded JSON
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except (json.JSONDecodeError, ValueError):
                return {}
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}
