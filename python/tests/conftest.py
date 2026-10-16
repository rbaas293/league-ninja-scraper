import pytest


@pytest.fixture(autouse=True)
def _clear_legacy_config_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the legacy STAGEHAND_VOLLEYBALL_CONFIG alias from leaking into tests."""
    monkeypatch.delenv("STAGEHAND_VOLLEYBALL_CONFIG", raising=False)
