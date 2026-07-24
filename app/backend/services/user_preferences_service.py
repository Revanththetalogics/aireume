"""Load and merge per-user preferences (notifications, seen modals, welcome flags)."""
import json
from copy import deepcopy

DEFAULT_PREFERENCES = {
    "notifications": {
        "emailOnComplete": True,
        "emailOnBatchComplete": True,
        "marketing": False,
    },
    "seen_modals": {},
    "invited_welcome_dismissed": False,
}


def _parse(raw) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        return {}


def load_preferences(user) -> dict:
    data = _parse(getattr(user, "preferences_json", None))
    merged = deepcopy(DEFAULT_PREFERENCES)
    if isinstance(data.get("notifications"), dict):
        merged["notifications"].update(data["notifications"])
    if isinstance(data.get("seen_modals"), dict):
        merged["seen_modals"] = {**merged["seen_modals"], **data["seen_modals"]}
    if "invited_welcome_dismissed" in data:
        merged["invited_welcome_dismissed"] = bool(data["invited_welcome_dismissed"])
    return merged


def save_preferences(user, preferences: dict, db) -> dict:
    user.preferences_json = json.dumps(preferences)
    db.commit()
    db.refresh(user)
    return load_preferences(user)


def merge_preferences(user, patch: dict, db) -> dict:
    current = load_preferences(user)
    if "notifications" in patch and isinstance(patch["notifications"], dict):
        current["notifications"].update(patch["notifications"])
    if "seen_modals" in patch and isinstance(patch["seen_modals"], dict):
        current["seen_modals"].update(patch["seen_modals"])
    if "invited_welcome_dismissed" in patch:
        current["invited_welcome_dismissed"] = bool(patch["invited_welcome_dismissed"])
    return save_preferences(user, current, db)


def mark_modal_seen(user, modal_id: str, db) -> dict:
    prefs = load_preferences(user)
    prefs["seen_modals"][modal_id] = True
    return save_preferences(user, prefs, db)
