"""환경변수 로딩.

테스트에서 환경변수를 바꿔 끼울 수 있도록 값을 캐시하지 않고 호출할 때마다 읽는다.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

PROVIDER_GEMINI = "gemini"
PROVIDER_ANTHROPIC = "anthropic"
PROVIDERS = (PROVIDER_GEMINI, PROVIDER_ANTHROPIC)

DEFAULT_PROVIDER = PROVIDER_GEMINI
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
# 생각(thinking) 정도. 낮을수록 빠르다. gemini-3.8-flash는 MINIMAL을 지원하지 않아 LOW를 쓴다.
DEFAULT_GEMINI_THINKING_LEVEL = "LOW"
DEFAULT_MODEL = "claude-haiku-5-5"

logger = logging.getLogger(__name__)


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("%s 값이 숫자가 아니어서 기본값 %s를 씁니다", name, default)
        return default


def _provider() -> str:
    raw = (os.getenv("LLM_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    if raw not in PROVIDERS:
        logger.warning("LLM_PROVIDER=%s 는 지원하지 않아 %s를 씁니다", raw, DEFAULT_PROVIDER)
        return DEFAULT_PROVIDER
    return raw


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    gemini_api_key: str | None
    gemini_model: str
    gemini_thinking_level: str
    anthropic_api_key: str | None
    claude_model: str
    sync_wait_sec: float
    mock_llm: bool
    mock_delay: float
    log_level: str

    @property
    def api_key(self) -> str | None:
        """현재 제공자에 맞는 API 키."""
        if self.llm_provider == PROVIDER_ANTHROPIC:
            return self.anthropic_api_key
        return self.gemini_api_key

    @property
    def api_key_name(self) -> str:
        if self.llm_provider == PROVIDER_ANTHROPIC:
            return "ANTHROPIC_API_KEY"
        return "GEMINI_API_KEY"


def get_settings() -> Settings:
    return Settings(
        llm_provider=_provider(),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL,
        gemini_thinking_level=(
            os.getenv("GEMINI_THINKING_LEVEL") or DEFAULT_GEMINI_THINKING_LEVEL
        ).upper(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        claude_model=os.getenv("CLAUDE_MODEL") or DEFAULT_MODEL,
        sync_wait_sec=_float("SYNC_WAIT_SEC", 4.0),
        mock_llm=os.getenv("MOCK_LLM", "0").strip() == "1",
        mock_delay=_float("MOCK_DELAY", 0.2),
        log_level=(os.getenv("LOG_LEVEL") or "INFO").upper(),
    )
