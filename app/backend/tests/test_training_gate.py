"""
Tests that the beta model-fine-tuning endpoint is gated:
  - disabled by default in production
  - enabled by default in non-production
  - explicit TRAINING_ENABLED override wins
  - POST /api/training/train returns 403 when disabled
"""
import pytest

from app.backend.routes.training import _training_enabled


class TestTrainingGateFlag:
    def test_defaults_enabled_in_development(self, monkeypatch):
        monkeypatch.delenv("TRAINING_ENABLED", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")
        assert _training_enabled() is True

    def test_defaults_disabled_in_production(self, monkeypatch):
        monkeypatch.delenv("TRAINING_ENABLED", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        assert _training_enabled() is False

    def test_explicit_true_overrides_production(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("TRAINING_ENABLED", "true")
        assert _training_enabled() is True

    def test_explicit_false_overrides_development(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("TRAINING_ENABLED", "false")
        assert _training_enabled() is False


class TestTrainingEndpointGate:
    def test_train_returns_403_when_disabled(self, auth_client, monkeypatch):
        monkeypatch.setenv("TRAINING_ENABLED", "false")
        resp = auth_client.post("/api/training/train")
        assert resp.status_code == 403
        assert "beta" in resp.json()["detail"].lower() or "disabled" in resp.json()["detail"].lower()
