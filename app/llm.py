"""Claude 호출. `MOCK_LLM=1`이면 API를 호출하지 않고 정해진 가짜 응답을 돌려준다.

어떤 오류가 나도 예외를 밖으로 던지지 않고 안내 문구를 돌려준다.
"""

from __future__ import annotations

import asyncio
import logging

import anthropic

from app.config import get_settings
from app.prompts import SYSTEM_PROMPT, build_user_prompt, settings_line

logger = logging.getLogger(__name__)

MAX_INPUT_LEN = 1000
MAX_TOKENS = 700
# 카카오 5초 제한 안에 끝나도록 생각(thinking)을 짧게 한다.
EFFORT = "low"
API_TIMEOUT_SEC = 30.0
API_MAX_RETRIES = 1

ERROR_MESSAGE = "앗, 문장을 다듬다가 오류가 났어요. 잠시 후 다시 보내 주세요 🙏"

MOCK_OUTPUT = """✅ 추천
(테스트용 가짜 응답) 안녕하세요, [이름]입니다. 말씀드릴 내용이 있어 연락드렸습니다.

🌿 조금 더 부드럽게
(테스트용 가짜 응답) 안녕하세요! [이름]이에요. 바쁘실 텐데 잠시 말씀드려도 될까요?

💡 한 줄 팁
실제 응답은 MOCK_LLM=0일 때 Claude가 만들어요."""

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(timeout=API_TIMEOUT_SEC, max_retries=API_MAX_RETRIES)
    return _client


async def _call_model(target: str, situation: str, text: str) -> str:
    """모델을 호출해 본문 텍스트를 돌려준다. 실패하면 예외를 던진다."""
    settings = get_settings()
    if settings.mock_llm:
        await asyncio.sleep(settings.mock_delay)
        return MOCK_OUTPUT

    response = await _get_client().messages.create(
        model=settings.claude_model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        output_config={"effort": EFFORT},
        messages=[{"role": "user", "content": build_user_prompt(target, situation, text)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("모델이 요청을 거절했습니다")
    output = "".join(block.text for block in response.content if block.type == "text").strip()
    if not output:
        raise RuntimeError(f"빈 응답 (stop_reason={response.stop_reason})")
    return output


async def correct(text: str, target: str, situation: str) -> str:
    """문장을 교정해 최종 답장 텍스트를 돌려준다. 예외를 던지지 않는다."""
    text = text[:MAX_INPUT_LEN]
    # 사용자 원문은 DEBUG에서만 남긴다.
    logger.debug("교정 요청 원문: %r", text)
    logger.info("교정 시작 target=%s situation=%s len=%d", target, situation, len(text))
    try:
        output = await _call_model(target, situation, text)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - 어떤 오류든 사용자에게는 안내 문구만 보낸다
        logger.error("교정 실패: %s: %s", type(exc).__name__, exc)
        return ERROR_MESSAGE
    return f"{settings_line(target, situation)}\n\n{output}"
