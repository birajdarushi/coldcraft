"""
LLM client — Google Gemini via the google-genai SDK.

Isolates the provider so the drafter (and any future caller) depends only on
`generate_json`. The client is created lazily so an unset API key never breaks
import time (the API can still boot; only drafting/intel calls will fail).
"""

from __future__ import annotations

import json
import os
import time

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")


class LLMError(RuntimeError):
    """Wraps provider errors with an HTTP-ish status for the API layer."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def _resolve_api_key() -> str | None:
    """Env wins (deploy-time override); otherwise the key saved via the UI."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    try:
        from .infrastructure.persistence.repositories import SQLAlchemyCampaignRepository

        return SQLAlchemyCampaignRepository().get_gemini_api_key()
    except Exception:
        return None


def _build_client():
    """Always builds from the currently-resolved key (no stale module cache),
    so a key saved through the UI takes effect on the next request."""
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError(
            "No Gemini API key configured. Set GEMINI_API_KEY in the environment "
            "or add it under Settings → API Keys."
        )
    return genai.Client(api_key=api_key)


def _strip_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
    return text.strip()


def _parse_json(text: str):
    """Extract the first complete JSON value, tolerating fences/preamble/trailing text."""
    cleaned = _strip_fences(text)
    start = next((i for i, ch in enumerate(cleaned) if ch in "{["), None)
    if start is None:
        return json.loads(cleaned)  # raises a clear error
    obj, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    return obj


def generate_json(system: str, prompt: str, max_tokens: int = 1000, model: str | None = None):
    """Call Gemini and parse a JSON object/array from the response.

    `response_mime_type=application/json` forces well-formed JSON output.
    Thinking is disabled so the token budget is spent on the answer, not
    internal reasoning (these are structured, deterministic tasks).
    """
    client = _build_client()
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
        temperature=0.7,
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    last_exc = None
    for attempt in range(3):  # retry transient overloads (503/500) with backoff
        try:
            response = client.models.generate_content(
                model=model or DEFAULT_MODEL, contents=prompt, config=cfg
            )
            return _parse_json(response.text)
        except genai_errors.ClientError as exc:
            status = getattr(exc, "code", 502) or 502
            if status == 429:
                raise LLMError(
                    "Gemini rate limit hit (free tier = 5 requests/min). "
                    "Wait ~60s and retry, or enable billing on the key.",
                    status=429,
                ) from exc
            raise LLMError(f"Gemini request failed ({status}): {exc}", status=status) from exc
        except genai_errors.ServerError as exc:  # 500/503 overload — transient
            last_exc = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise LLMError("Gemini is temporarily overloaded (503). Please retry.", status=503) from exc
        except genai_errors.APIError as exc:
            raise LLMError(f"Gemini service error: {exc}", status=502) from exc
    raise LLMError("Gemini call failed after retries.", status=503) from last_exc
