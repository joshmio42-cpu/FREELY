from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.config import Settings
from app.main import require_internal_token
from app.pipeline import PipelineService
from app.sources.remoteok import fetch_remoteok
from app.telegram_commands import TelegramCommandPoller


def request_with(settings: Settings) -> SimpleNamespace:
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)))


def test_internal_api_authentication_fails_closed_when_token_is_missing() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_internal_token(request_with(Settings(internal_api_token="")), None)
    assert exc_info.value.status_code == 503


def test_internal_api_authentication_rejects_wrong_token() -> None:
    settings = Settings(internal_api_token="correct-test-token")
    with pytest.raises(HTTPException) as exc_info:
        require_internal_token(request_with(settings), "wrong-test-token")
    assert exc_info.value.status_code == 401


def test_settings_repr_redacts_secrets() -> None:
    marker = "test-secret-that-must-not-appear"
    settings = Settings(internal_api_token=marker, telegram_bot_token=marker)
    assert marker not in repr(settings)
    assert marker not in str(settings.model_dump())


@pytest.mark.asyncio
async def test_telegram_transport_error_does_not_expose_token() -> None:
    marker = "synthetic-test-token-that-must-stay-private"
    settings = Settings(telegram_bot_token=marker, telegram_chat_id="123456789")
    poller = TelegramCommandPoller(settings, SimpleNamespace(spec=PipelineService))

    class FailingClient:
        async def post(self, url: str, **kwargs):
            request = httpx.Request("POST", url)
            raise httpx.ConnectError("connection failed", request=request)

    poller._client = FailingClient()  # type: ignore[assignment]
    with pytest.raises(RuntimeError) as exc_info:
        await poller._api("getUpdates", {"timeout": 0})
    assert marker not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


@pytest.mark.asyncio
async def test_remoteok_source_rejects_nonofficial_url_before_request() -> None:
    with pytest.raises(ValueError, match="official Remote OK host"):
        await fetch_remoteok("http://127.0.0.1:8000/private", 1)
