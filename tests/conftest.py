"""테스트 공통 설정. 실제 API를 절대 호출하지 않도록 mock 모드를 강제한다."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ["MOCK_LLM"] = "1"
os.environ.setdefault("MOCK_DELAY", "0.01")
for _key in (
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "LLM_PROVIDER",
    "GEMINI_MODEL",
    "GEMINI_THINKING_LEVEL",
):
    os.environ.pop(_key, None)


@pytest.fixture
def client():
    """요청 사이에 백그라운드 태스크가 살아 있도록 이벤트 루프를 유지한다."""
    from app.main import app

    with TestClient(app) as c:
        yield c


def kakao_body(utterance: str, user_id: str = "user-1", callback_url: str | None = None) -> dict:
    user_request: dict = {"utterance": utterance, "user": {"id": user_id}}
    if callback_url:
        user_request["callbackUrl"] = callback_url
    return {"userRequest": user_request}
