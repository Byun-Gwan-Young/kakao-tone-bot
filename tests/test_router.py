"""라우팅 검증 (SPEC 7-2, 7-4)."""

import pytest

from app.prompts import SITUATIONS, TARGETS
from app.router import MAIN_QR, CorrectionRequest, Reply, route
from app.state import UserState
from tests.test_kakao_format import assert_valid_kakao


def _text(reply: Reply) -> str:
    return reply.response["template"]["outputs"][0]["simpleText"]["text"]


def _labels(reply: Reply) -> list[str]:
    return [q["label"] for q in reply.response["template"].get("quickReplies", [])]


@pytest.mark.parametrize("utt", ["", "도움말", "시작", "처음", "사용법", "  도움말  "])
def test_help(utt):
    reply = route(utt, UserState())
    assert isinstance(reply, Reply)
    assert_valid_kakao(reply.response)
    assert "현재 설정" in _text(reply)
    assert "받는 사람: 상사" in _text(reply)
    assert _labels(reply) == MAIN_QR


def test_change_target_buttons():
    reply = route("받는 사람 바꾸기", UserState())
    assert isinstance(reply, Reply)
    assert_valid_kakao(reply.response)
    assert "누구에게" in _text(reply)
    assert _labels(reply) == [f"대상:{t}" for t in TARGETS]


def test_change_situation_buttons():
    reply = route("상황 바꾸기", UserState())
    assert isinstance(reply, Reply)
    assert_valid_kakao(reply.response)
    assert "어떤 상황" in _text(reply)
    assert _labels(reply) == [f"상황:{s}" for s in SITUATIONS]


def test_set_target():
    st = UserState()
    reply = route("대상:교수님", st)
    assert isinstance(reply, Reply)
    assert st.target == "교수님"
    assert "설정했어요!" in _text(reply)
    assert "받는 사람: 교수님" in _text(reply)
    assert _labels(reply) == MAIN_QR


def test_set_situation():
    st = UserState()
    reply = route("상황:조의(부고)", st)
    assert isinstance(reply, Reply)
    assert st.situation == "조의(부고)"
    assert "상황: 조의(부고)" in _text(reply)


def test_unknown_target_is_corrected():
    st = UserState()
    result = route("대상:외계인", st)
    assert isinstance(result, CorrectionRequest)
    assert result.text == "대상:외계인"
    assert st.target == "상사"


def test_plain_sentence_is_corrected_with_current_settings():
    st = UserState(target="선배", situation="감사")
    result = route("어제 밥 사주셔서 감사", st)
    assert result == CorrectionRequest(
        text="어제 밥 사주셔서 감사", target="선배", situation="감사"
    )


def test_result_without_any_result():
    reply = route("결과 보기", UserState())
    assert isinstance(reply, Reply)
    assert "아직 다듬은 문장이 없어요" in _text(reply)


def test_result_shows_last_result():
    st = UserState(last_result="✅ 추천\n좋은 문장")
    reply = route("결과 보기", st)
    assert isinstance(reply, Reply)
    assert _text(reply) == "✅ 추천\n좋은 문장"
    assert _labels(reply) == MAIN_QR


async def test_result_while_pending():
    import asyncio

    st = UserState()
    st.pending = asyncio.create_task(asyncio.sleep(1))
    try:
        reply = route("결과 보기", st)
        assert isinstance(reply, Reply)
        assert "아직 다듬는 중" in _text(reply)
        assert _labels(reply) == ["결과 보기"]
    finally:
        st.pending.cancel()


def test_safety_rule_resets_situation_when_only_target_given():
    """조의 설정 후 받는 사람만 지정하면 상황이 일반으로 초기화된다 (SPEC 7-4)."""
    st = UserState()
    route("상황:조의(부고)", st)
    assert st.situation == "조의(부고)"

    result = route("거래처: 견적서 언제 와요", st)
    assert isinstance(result, CorrectionRequest)
    assert st.target == "거래처·고객"
    assert st.situation == "일반"
    assert result == CorrectionRequest(
        text="견적서 언제 와요", target="거래처·고객", situation="일반"
    )


def test_situation_only_keeps_target():
    st = UserState(target="교수님")
    result = route("감사: 추천서 써주셔서 감사해요", st)
    assert isinstance(result, CorrectionRequest)
    assert st.target == "교수님"
    assert st.situation == "감사"


def test_inline_settings_persist():
    st = UserState()
    route("교수님/결석: 내일 못가요", st)
    result = route("과제 늦게 내도 될까요", st)
    assert result == CorrectionRequest(
        text="과제 늦게 내도 될까요", target="교수님", situation="결석·지각·연차"
    )
