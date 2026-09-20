import asyncio
import logging
from contextlib import suppress
from typing import Any

import httpx

from app.config import Settings
from app.pipeline import PipelineService

logger = logging.getLogger(__name__)


def is_run_command(text: str) -> bool:
    parts = text.strip().split()
    if not parts:
        return False
    command = parts[0].split("@", maxsplit=1)[0].casefold()
    if len(parts) == 1:
        return command == "/go"
    return len(parts) == 2 and command == "/run" and parts[1].casefold() == "freely"


def render_run_summary(result: dict[str, Any]) -> str:
    source_lines = []
    total_fetched = 0
    total_candidates = 0
    for scout in result.get("scouts", []):
        fetched = int(scout.get("fetched", 0))
        candidates = len(scout.get("opportunity_ids", []))
        total_fetched += fetched
        total_candidates += candidates
        source_lines.append(
            f"• {scout.get('platform', 'source')}: {fetched} fetched, {candidates} candidates"
        )

    processed = result.get("processed", [])
    proposals = sum(1 for item in processed if item.get("deliver"))
    rejected = sum(1 for item in processed if item.get("status") == "REJECTED")
    errors = len(result.get("errors", [])) + len(result.get("source_errors", []))
    freelancer_alerts = result.get("freelancer_alerts", {})
    queued_alerts = int(freelancer_alerts.get("queued_found", 0))
    details_needed = int(freelancer_alerts.get("details_needed", 0))
    lines = [
        "FREELY run finished.",
        "",
        "Mode: Freelancer saved-search alerts only",
        f"Queued alerts found: {queued_alerts}",
        f"AI evaluations: {len(processed)}",
        f"Proposals prepared: {proposals}",
        f"Skipped as unsafe or undeliverable: {rejected}",
        f"Errors: {errors}",
        f"Alerts needing the full brief opened manually: {details_needed}",
    ]
    if source_lines:
        lines.extend(["", "Sources:", *source_lines])
    return "\n".join(lines)


class TelegramCommandPoller:
    def __init__(self, settings: Settings, pipeline: PipelineService):
        self.settings = settings
        self.pipeline = pipeline
        self._poll_task: asyncio.Task[None] | None = None
        self._run_task: asyncio.Task[None] | None = None
        self._offset: int | None = None
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if not self.settings.telegram_commands_enabled:
            logger.info("Telegram command polling disabled: token or chat ID missing")
            return
        self._client = httpx.AsyncClient(timeout=self.settings.telegram_poll_timeout + 10)
        self._poll_task = asyncio.create_task(self._poll_loop(), name="telegram-command-poller")

    async def stop(self) -> None:
        for task in (self._poll_task, self._run_task):
            if task and not task.done():
                task.cancel()
        for task in (self._poll_task, self._run_task):
            if task:
                with suppress(asyncio.CancelledError):
                    await task
        if self._client:
            await self._client.aclose()

    async def _api(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("Telegram client is not started")
        token = self.settings.telegram_bot_token.get_secret_value()
        url = f"https://api.telegram.org/bot{token}/{method}"
        try:
            response = await self._client.post(url, json=payload, follow_redirects=False)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("Telegram %s transport failure: %s", method, type(exc).__name__)
            raise RuntimeError(f"Telegram {method} request failed") from None
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method} failed")
        return body

    async def _prime_offset(self) -> None:
        body = await self._api("getUpdates", {"offset": -1, "limit": 1, "timeout": 0})
        updates = body.get("result", [])
        if updates:
            self._offset = int(updates[-1]["update_id"]) + 1

    async def _poll_loop(self) -> None:
        primed = False
        while True:
            try:
                if not primed:
                    await self._prime_offset()
                    primed = True
                payload: dict[str, Any] = {
                    "timeout": self.settings.telegram_poll_timeout,
                    "allowed_updates": ["message"],
                }
                if self._offset is not None:
                    payload["offset"] = self._offset
                body = await self._api("getUpdates", payload)
                for update in body.get("result", []):
                    self._offset = int(update["update_id"]) + 1
                    await self._handle_update(update)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Telegram polling failed; retrying")
                await asyncio.sleep(5)

    async def _handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or {}
        chat_id = str((message.get("chat") or {}).get("id", ""))
        text = message.get("text")
        if (
            chat_id != self.settings.telegram_chat_id.get_secret_value()
            or not isinstance(text, str)
        ):
            return
        if not is_run_command(text):
            return
        if self._run_task and not self._run_task.done():
            await self._send(
                chat_id,
            "FREELY is already running. I will send a summary when it finishes.",
            )
            return
        self._run_task = asyncio.create_task(self._run_pipeline(chat_id), name="telegram-freely-run")

    async def _run_pipeline(self, chat_id: str) -> None:
        await self._send(
            chat_id,
            "FREELY is running. I am reviewing up to 5 queued Freelancer alerts now. "
            "I will send each usable lead with its exact link and proposal, then a summary.",
        )
        try:
            result = await self.pipeline.scout_and_process(concurrency=2)
            for item in result.get("processed", []):
                if item.get("deliver"):
                    for chunk in item.get("telegram_chunks", []):
                        await self._send(chat_id, chunk)
            for chunk in result.get("freelancer_alerts", {}).get("notifications", []):
                await self._send(chat_id, chunk)
            await self._send(chat_id, render_run_summary(result))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Telegram-triggered FREELY run failed")
            await self._send(
                chat_id,
                "FREELY run failed before completion. Check the API logs; no bids were submitted.",
            )

    async def send_message(self, text: str) -> bool:
        """Send a system-generated notification to the configured user chat."""
        if not self.settings.telegram_commands_enabled or not self._client:
            return False
        await self._send(self.settings.telegram_chat_id.get_secret_value(), text)
        return True

    async def send_chunks(self, chunks: list[str]) -> int:
        sent = 0
        for chunk in chunks:
            if await self.send_message(chunk):
                sent += 1
        return sent

    async def _send(self, chat_id: str, text: str) -> None:
        for attempt in range(3):
            try:
                await self._api(
                    "sendMessage",
                    {"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
                )
                return
            except RuntimeError:
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
        raise RuntimeError("Telegram message delivery failed after 3 attempts") from None
