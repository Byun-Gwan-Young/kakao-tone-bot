"""환경변수 로딩.

테스트에서 환경변수를 바꿔 끼울 수 있도록 값을 캐시하지 않고 호출할 때마다 읽는다.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

DEFAULT_MODEL = "claude-haiku-5-5"


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logging.getLogger(__name__).warning(
            "%s 값이 숫자가 아니어서 기본값 %s를 씁니다", name, default
        )
        return default


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None
    claude_model: str
    sync_wait_sec: float
    mock_llm: bool
    mock_delay: float
    log_level: str


def get_settings() -> Settings:
    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        claude_model=os.getenv("CLAUDE_MODEL") or DEFAULT_MODEL,
        sync_wait_sec=_float("SYNC_WAIT_SEC", 4.0),
        mock_llm=os.getenv("MOCK_LLM", "0").strip() == "1",
        mock_delay=_float("MOCK_DELAY", 0.2),
        log_level=(os.getenv("LOG_LEVEL") or "INFO").upper(),
    )
