"""카카오 응답 형식 검증 (SPEC 7-1)."""

from app.kakao import (
    MAX_LABEL_LEN,
    MAX_QUICK_REPLIES,
    callback_ack_response,
    parse_request,
    quick_replies,
    text_response,
    truncate_text,
)


def assert_valid_kakao(resp: dict) -> None:
    """4.2 규격을 지키는지 검사한다. 다른 테스트에서도 재사용한다."""
    assert resp["version"] == "2.0"
    outputs = resp["template"]["outputs"]
    assert isinstance(outputs, list) and outputs
    for out in outputs:
        text = out["simpleText"]["text"]
        assert isinstance(text, str)
        assert len(text) <= 1000
    qrs = resp["template"].get("quickReplies", [])
    assert len(qrs) <= MAX_QUICK_REPLIES
    for qr in qrs:
        assert len(qr["label"]) <= MAX_LABEL_LEN
        assert qr["action"] == "message"
        assert qr["messageText"]


def test_text_response_structure():
    resp = text_response("안녕하세요", ["받는 사람 바꾸기", "상황 바꾸기", "도움말"])
    assert_valid_kakao(resp)
    assert resp["template"]["outputs"][0]["simpleText"]["text"] == "안녕하세요"
    assert [q["label"] for q in resp["template"]["quickReplies"]] == [
        "받는 사람 바꾸기",
        "상황 바꾸기",
        "도움말",
    ]


def test_text_response_without_buttons_has_no_quick_replies():
    resp = text_response("hi")
    assert_valid_kakao(resp)
    assert "quickReplies" not in resp["template"]


def test_long_text_is_truncated_to_1000():
    resp = text_response("가" * 1500)
    text = resp["template"]["outputs"][0]["simpleText"]["text"]
    assert len(text) == 1000
    assert text.endswith("…")
    assert text[:999] == "가" * 999


def test_truncate_keeps_short_text():
    assert truncate_text("가" * 1000) == "가" * 1000


def test_quick_replies_capped_at_10_and_label_14():
    labels = [f"아주아주아주아주아주긴버튼라벨{i}" for i in range(15)]
    qrs = quick_replies(labels)
    assert len(qrs) == 10
    assert all(len(q["label"]) <= 14 for q in qrs)
    # 눌렀을 때 보내는 문장은 원래 라벨 그대로
    assert qrs[0]["messageText"] == labels[0]


def test_callback_ack_response():
    resp = callback_ack_response("잠시만요")
    assert resp == {"version": "2.0", "useCallback": True, "data": {"text": "잠시만요"}}


def test_parse_full_request():
    req = parse_request(
        {
            "userRequest": {
                "utterance": "  안녕  ",
                "user": {"id": "abc"},
                "callbackUrl": "https://example.com/cb",
            }
        }
    )
    assert req.utterance == "안녕"
    assert req.user_id == "abc"
    assert req.callback_url == "https://example.com/cb"


def test_parse_broken_requests_do_not_raise():
    for body in [{}, None, [], "x", {"userRequest": None}, {"userRequest": {"user": "x"}}]:
        req = parse_request(body)
        assert req.utterance == ""
        assert req.user_id
        assert req.callback_url is None
