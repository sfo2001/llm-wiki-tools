"""Provider-agnostic LLM client for unattended lwt jobs (maintain, ingest review).

Not used by interactive ingest/authoring — see ADR-0007. Callers must treat a
``None`` return from :func:`load_llm_config` as "no provider configured" and
skip the LLM-backed step entirely (degrade to structural-lint-only behavior).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

import requests

_VALID_FORMATS = ("openai", "anthropic")
_TIMEOUT = 30


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str = field(repr=False)
    api_format: str
    model: str
    fallback: LLMConfig | None = None


def _load_one(env: Mapping[str, str], prefix: str) -> LLMConfig | None:
    base_url = env.get(f"{prefix}_API_BASE_URL", "").strip()
    if not base_url:
        return None
    api_format = env.get(f"{prefix}_API_FORMAT", "openai")
    if api_format not in _VALID_FORMATS:
        raise ValueError(
            f"{prefix}_API_FORMAT must be one of {_VALID_FORMATS}, got {api_format!r}"
        )
    return LLMConfig(
        base_url=base_url,
        api_key=env.get(f"{prefix}_API_KEY", ""),
        api_format=api_format,
        model=env.get(f"{prefix}_MODEL", ""),
    )


def load_llm_config(env: Mapping[str, str] | None = None) -> LLMConfig | None:
    """Load LLM provider config from environment variables.

    Returns None when LLM_API_BASE_URL is unset/empty — callers must treat
    that as "no provider configured" and skip the LLM-backed step.
    """
    if env is None:
        env = os.environ
    primary = _load_one(env, "LLM")
    if primary is None:
        return None
    try:
        fallback = _load_one(env, "LLM_FALLBACK")
    except ValueError:
        # A broken fallback must not take down an otherwise-valid primary
        # config for an unattended job — degrade to "no fallback."
        fallback = None
    if fallback is not None:
        primary = LLMConfig(
            base_url=primary.base_url,
            api_key=primary.api_key,
            api_format=primary.api_format,
            model=primary.model,
            fallback=fallback,
        )
    return primary


class LLMClientError(Exception):
    """Raised when a completion request fails against primary and any fallback."""


class LLMClient:
    """Sends chat completions to a configured provider, falling back on failure."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete(self, messages: list[dict], *, system: str | None = None) -> str:
        try:
            return self._complete_with(self.config, messages, system=system)
        except (requests.RequestException, LLMClientError) as primary_error:
            if self.config.fallback is None:
                raise LLMClientError(
                    f"LLM request failed: {primary_error}"
                ) from primary_error
            try:
                return self._complete_with(
                    self.config.fallback, messages, system=system
                )
            except (requests.RequestException, LLMClientError) as fallback_error:
                raise LLMClientError(
                    f"LLM request failed on primary ({primary_error}) "
                    f"and fallback ({fallback_error})"
                ) from fallback_error

    def _complete_with(
        self, config: LLMConfig, messages: list[dict], *, system: str | None
    ) -> str:
        if config.api_format == "openai":
            return self._complete_openai(config, messages)
        if config.api_format == "anthropic":
            return self._complete_anthropic(config, messages, system=system)
        raise LLMClientError(f"Unsupported api_format: {config.api_format!r}")

    def _complete_openai(self, config: LLMConfig, messages: list[dict]) -> str:
        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        resp = requests.post(
            f"{config.base_url.rstrip('/')}/chat/completions",
            json={"model": config.model, "messages": messages},
            headers=headers,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMClientError(
                f"Unexpected response shape from {config.base_url}: {e}"
            ) from e

    def _complete_anthropic(
        self, config: LLMConfig, messages: list[dict], *, system: str | None
    ) -> str:
        headers = {
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if config.api_key:
            headers["x-api-key"] = config.api_key
        payload: dict = {
            "model": config.model,
            "messages": messages,
            "max_tokens": 4096,
        }
        if system is not None:
            payload["system"] = system
        resp = requests.post(
            f"{config.base_url.rstrip('/')}/messages",
            json=payload,
            headers=headers,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        try:
            return resp.json()["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMClientError(
                f"Unexpected response shape from {config.base_url}: {e}"
            ) from e
