"""FastAPI 앱: 카카오 i 오픈빌더 스킬 서버.

- `GET /`      헬스체크
- `POST /skill` 스킬 요청 처리 (5초 제한: 콜백 모드 / 동기 모드)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request

from app import llm
from app.config import get_settings
from app.kakao import callback_ack_response, parse_request, text_response
from app.router import MAIN_QR, RESULT_QR, CorrectionRequest, Reply, route
from app.state import MemoryStateStore, StateStore, UserState

logger = logging.getLogger(__name__)

CALLBACK_ACK_TEXT = "말투 다듬는 중이에요 ✍️ 잠시만요!"
SYNC_TIMEOUT_TEXT = "문장을 다듬고 있어요 ✍️ 몇 초 뒤 '결과 보기'를 눌러 주세요."
INTERNAL_ERROR_TEXT = "앗, 잠시 문제가 생겼어요. 다시 보내 주세요 🙏"
CALLBACK_TIMEOUT_SEC = 10.0

# 백그라운드 태스크가 가비지 컬렉션되지 않도록 참조를 들고 있는다.
_background_tasks: set[asyncio.Task] = set()


def _spawn(coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logging.getLogger().setLevel(settings.log_level)
    if settings.mock_llm:
        logger.info("MOCK_LLM=1: Claude API를 호출하지 않고 가짜 응답을 씁니다")
    elif not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY가 설정되지 않았습니다. 교정 요청이 실패합니다")
    app.state.store = MemoryStateStore()
    yield
    for task in list(_background_tasks):
        task.cancel()


app = FastAPI(title="kakao-tone-bot", lifespan=lifespan)


def _get_store(request: Request) -> StateStore:
    store = getattr(request.app.state, "store", None)
    if store is None:  # lifespan 없이 쓰인 경우 대비
        store = request.app.state.store = MemoryStateStore()
    return store


async def _correct_and_save(req: CorrectionRequest, state: UserState) -> str:
    """교정 후 결과를 사용자 상태에 직접 저장한다."""
    text = await llm.correct(req.text, req.target, req.situation)
    state.last_result = text
    state.touch()
    return text


async def _correct_and_callback(req: CorrectionRequest, state: UserState, url: str) -> None:
    """콜백 모드: 교정 결과를 callbackUrl로 POST한다. 실패해도 재시도하지 않는다."""
    text = await _correct_and_save(req, state)
    try:
        async with httpx.AsyncClient(timeout=CALLBACK_TIMEOUT_SEC) as client:
            resp = await client.post(url, json=text_response(text, MAIN_QR))
        if resp.status_code >= 400:
            logger.error("콜백 전송 실패: HTTP %s", resp.status_code)
        else:
            logger.info("콜백 전송 완료: HTTP %s", resp.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.error("콜백 전송 오류: %s: %s", type(exc).__name__, exc)


async def _handle_correction(
    req: CorrectionRequest, state: UserState, callback_url: str | None
) -> dict:
    if callback_url:
        state.pending = _spawn(_correct_and_callback(req, state, callback_url))
        return callback_ack_response(CALLBACK_ACK_TEXT)

    task = _spawn(_correct_and_save(req, state))
    state.pending = task
    try:
        # shield: 시간이 지나도 교정 작업은 취소하지 않는다.
        text = await asyncio.wait_for(asyncio.shield(task), timeout=get_settings().sync_wait_sec)
    except TimeoutError:
        logger.info("동기 대기 시간 초과: 결과 보기 안내")
        return text_response(SYNC_TIMEOUT_TEXT, RESULT_QR)
    return text_response(text, MAIN_QR)


@app.get("/")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/skill")
async def skill(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - 잘못된 JSON도 도움말로 응답
        body = {}
    req = parse_request(body)
    logger.debug("발화 원문: %r", req.utterance)

    try:
        state = _get_store(request).get(req.user_id)
        result = route(req.utterance, state)
        if isinstance(result, Reply):
            return result.response
        return await _handle_correction(result, state, req.callback_url)
    except Exception:  # noqa: BLE001 - 어떤 경우에도 500을 내지 않는다
        logger.exception("스킬 처리 중 예기치 못한 오류")
        return text_response(INTERNAL_ERROR_TEXT, MAIN_QR)
