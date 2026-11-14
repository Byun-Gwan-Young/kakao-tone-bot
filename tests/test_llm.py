"""LLM 호출 래퍼 검증. 실제 API는 절대 호출하지 않는다 (SPEC 7-7 일부)."""

from types import SimpleNamespace

import pytest

from app import llm


async def test_mock_output_has_header_and_sections():
    result = await llm.correct("내일 못가요", "교수님", "결석·지각·연차")
    assert result.startswith("🎯 받는 사람: 교수님  |  📌 상황: 결석·지각·연차\n\n")
    for section in ("✅ 추천", "🌿 조금 더 부드럽게", "💡 한 줄 팁"):
        assert section in result


async def test_exception_returns_error_message(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("API 터짐")

    monkeypatch.setattr(llm, "_call_model", boom)
    assert await llm.correct("안녕", "상사", "일반") == llm.ERROR_MESSAGE


class _FakeMessages:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        if self.exc:
            raise self.exc
        return self.response


def _fake_client(monkeypatch, messages):
    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.setattr(llm, "_get_client", lambda: SimpleNamespace(messages=messages))


async def test_real_path_builds_request_and_truncates_input(monkeypatch):
    messages = _FakeMessages(
        response=SimpleNamespace(
            stop_reason="end_turn",
            content=[
                SimpleNamespace(type="thinking", thinking=""),
                SimpleNamespace(type="text", text="✅ 추천\n좋아요"),
            ],
        )
    )
    _fake_client(monkeypatch, messages)

    result = await llm.correct("가" * 1500, "상사", "조의(부고)")

    assert result == "🎯 받는 사람: 상사  |  📌 상황: 조의(부고)\n\n✅ 추천\n좋아요"
    kw = messages.kwargs
    assert kw["max_tokens"] == 700
    assert kw["system"] == llm.SYSTEM_PROMPT
    user_prompt = kw["messages"][0]["content"]
    assert "조의(부고)" in user_prompt and "이모티콘" in user_prompt
    assert '"""\n' + "가" * 1000 + '\n"""' in user_prompt
    assert "가" * 1001 not in user_prompt


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(stop_reason="refusal", content=[]),
        SimpleNamespace(stop_reason="max_tokens", content=[]),
    ],
)
async def test_refusal_or_empty_returns_error_message(monkeypatch, response):
    _fake_client(monkeypatch, _FakeMessages(response=response))
    assert await llm.correct("안녕", "상사", "일반") == llm.ERROR_MESSAGE


async def test_api_exception_returns_error_message(monkeypatch):
    _fake_client(monkeypatch, _FakeMessages(exc=ConnectionError("네트워크 오류")))
    assert await llm.correct("안녕", "상사", "일반") == llm.ERROR_MESSAGE
