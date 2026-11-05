"""Gemini turns a Finnish query into validated search filters or a clarifying question."""

from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .search import NATURA_HIT_MIN_HA, SearchFilters

# Cheapest model available to new API keys (checked 2026-11-05): free tier, paid
# $0.25 in / $1.50 out per 1M tokens. gemini-2.5-flash-lite is cheaper on the price
# list but returns 404 "no longer available to new users". Override with GEMINI_MODEL.
DEFAULT_MODEL = "gemini-3.1-flash-lite"

SYSTEM_PROMPT = f"""\
You turn Finnish search requests about forest stands (metsäkuviot) near Joensuu into search filters.

Each stand has: area in hectares, Natura 2000 overlap in hectares, and the Natura 2000 share as a
percent of the stand area. A stand "overlaps a Natura 2000 site" when the overlap is at least
{NATURA_HIT_MIN_HA} ha.

Reply with JSON only:
- action "search" with "filters" when every condition in the request has an exact numeric meaning
  or maps to the natura rule ("osuu Natura-alueelle" -> natura "overlaps", "ei Natura-alueella" ->
  natura "outside", "kokonaan Natura-alueella" -> min_natura_pct 100).
- action "clarify" with one short Finnish "question" when a condition is vague, such as "iso",
  "pieni", "laaja" or "suuri osa", and the conversation has not yet given it a number. Ask about
  the vague part only. Never invent thresholds.
- If the request is not about searching forest stands, use "clarify" and ask in Finnish what kind
  of stands the user wants to find.

Combine the user's earlier request and their answers into one set of filters. "Yli X" and
"vähintään X" both become a minimum of X; "alle X" and "enintään X" become a maximum of X.
Convert units: 1 ha = 10 000 m².
"""


_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def ai_enabled() -> bool:
    """AI search switch from the ``AI_ENABLED`` environment variable (default: true)."""
    value = os.environ.get("AI_ENABLED", "true").strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(f"AI_ENABLED must be one of {sorted(_TRUE | _FALSE)}, got {value!r}")


class AssistantReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["search", "clarify"]
    question: str | None = Field(None, description="Finnish clarifying question when action is 'clarify'.")
    filters: SearchFilters | None = Field(None, description="Search filters when action is 'search'.")

    @model_validator(mode="after")
    def _check_action(self) -> AssistantReply:
        if self.action == "search" and self.filters is None:
            raise ValueError("a search reply needs filters")
        if self.action == "clarify" and not (self.question or "").strip():
            raise ValueError("a clarify reply needs a question")
        return self


class AssistantError(RuntimeError):
    """Shown to the user in Finnish."""


class AssistantUnavailable(AssistantError):
    pass


Turn = dict[str, str]  # {"role": "user" | "model", "text": ...}


# Next-cheapest model, used only when the default one is overloaded (503) or rate-limited (429).
DEFAULT_FALLBACK_MODEL = "gemini-3.5-flash-lite"
TIMEOUT_MS = 20_000
OVERLOAD_STATUSES = {429, 503}


class Assistant:
    def __init__(self, client: Any | None = None, model: str | None = None, fallback_model: str | None = None):
        self._client = client
        self.model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        fallback = fallback_model or os.environ.get("GEMINI_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL)
        self.fallback_model = fallback if fallback and fallback != self.model else None

    def _get_client(self):
        if self._client is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise AssistantUnavailable(
                    "Keskusteluhaku ei ole käytössä, koska GEMINI_API_KEY-avainta ei ole asetettu. "
                    "Voit rajata kuvioita Suodattimet-painikkeella."
                )
            from google import genai
            from google.genai import types

            # Fail fast: the SDK's default retries can keep a request waiting for minutes
            # when the model is overloaded, which leaves the UI stuck on its status message.
            self._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=TIMEOUT_MS,
                    retry_options=types.HttpRetryOptions(attempts=2, initial_delay=1.0, max_delay=4.0),
                ),
            )
        return self._client

    def _generate(self, client, model: str, contents: list[dict]):
        return client.models.generate_content(
            model=model,
            contents=contents,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "response_mime_type": "application/json",
                "response_json_schema": AssistantReply.model_json_schema(),
                "temperature": 0,
            },
        )

    def reply(self, history: list[Turn]) -> AssistantReply:
        client = self._get_client()
        contents = [{"role": t["role"], "parts": [{"text": t["text"]}]} for t in history]
        try:
            try:
                response = self._generate(client, self.model, contents)
            except Exception as exc:
                if self.fallback_model and getattr(exc, "code", None) in OVERLOAD_STATUSES:
                    response = self._generate(client, self.fallback_model, contents)
                else:
                    raise
        except Exception as exc:  # noqa: BLE001 - network and API errors alike
            if getattr(exc, "code", None) in OVERLOAD_STATUSES:
                raise AssistantError(
                    "Hakupalvelu on juuri nyt ruuhkautunut. Yritä hetken kuluttua uudelleen tai käytä suodattimia."
                ) from exc
            raise AssistantError(f"Hakupalvelu ei vastannut onnistuneesti: {exc}") from exc
        try:
            return AssistantReply.model_validate_json(response.text or "")
        except ValidationError as exc:
            raise AssistantError("Haun tulkinta epäonnistui: mallin vastaus ei ollut kelvollinen hakuehto.") from exc
