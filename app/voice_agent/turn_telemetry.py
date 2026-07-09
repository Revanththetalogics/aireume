"""Per-turn latency telemetry for voice screening calls."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TurnTelemetryCollector:
    """Accumulates timing metrics for each candidate→bot turn."""

    turns: list[dict[str, Any]] = field(default_factory=list)
    _current: dict[str, Any] = field(default_factory=dict, repr=False)
    _turn_index: int = 0

    def begin_turn(self) -> None:
        self._turn_index += 1
        self._current = {"turn": self._turn_index, "recorded_at": time.time()}

    def record(self, key: str, value: Any) -> None:
        self._current[key] = value

    def end_turn(self) -> None:
        if self._current:
            self.turns.append(dict(self._current))
            self._current = {}

    def summary(self) -> dict[str, Any]:
        if not self.turns:
            return {"turn_count": 0}
        keys = ("stt_ms", "think_ms", "tts_ms", "playback_ms", "turn_gap_ms")
        out: dict[str, Any] = {"turn_count": len(self.turns)}
        for key in keys:
            vals = [t[key] for t in self.turns if isinstance(t.get(key), (int, float))]
            if vals:
                vals.sort()
                out[f"{key}_p50"] = round(vals[len(vals) // 2], 1)
                out[f"{key}_p95"] = round(vals[max(0, int(len(vals) * 0.95) - 1)], 1)
        return out

    def as_result_payload(self) -> dict[str, Any]:
        return {"turns": self.turns, "summary": self.summary()}
