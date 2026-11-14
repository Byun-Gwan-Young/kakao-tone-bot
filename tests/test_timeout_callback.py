"""/skill 통합 테스트: 동기 모드 타임아웃, 콜백 모드, 오류 처리, 잘못된 요청 (SPEC 7-5~7-8)."""

import json
import time

import httpx
import respx

from app import llm
from app.main import CALLBACK_ACK_TEXT, SYNC_TIMEOUT_TEXT
from tests.conftest import kakao_body
from tests.test_kakao_format import assert_valid_kakao

CALLBACK_URL = "https://callback.example.com/cb/abc"


def _text(resp: dict) -> str:
    return resp["template"]["outputs"][0]["simpleText"]["text"]


def _labels(resp: dict) -> list[str]:
    return [q["label"] for q in resp["template"].get("quickReplies", [])]


def _wait_until(cond, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


def test_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_empty_body_returns_help(client):
    r = client.post("/skill", json={})
    assert r.status_code == 200
    data = r.json()
    assert_valid_kakao(data)
    assert "현재 설정" in _text(data)


def test_invalid_json_returns_help(client):
    r = client.post("/skill", content=b"not json", headers={"content-type": "application/json"})
    assert r.status_code == 200
    assert "현재 설정" in _text(r.json())


def test_settings_flow_end_to_end(client):
    r = client.post("/skill", json=kakao_body("대상:교수님"))
    assert "받는 사람: 교수님" in _text(r.json())
    r = client.post("/skill", json=kakao_body("도움말"))
    assert "받는 사람: 교수님" in _text(r.json())
    # 다른 사용자는 영향 없음
    r = client.post("/skill", json=kakao_body("도움말", user_id="user-2"))
    assert "받는 사람: 상사" in _text(r.json())


def test_sync_mode_returns_result_in_time(client, monkeypatch):
    monkeypatch.setenv("SYNC_WAIT_SEC", "2.0")
    monkeypatch.setenv("MOCK_DELAY", "0.01")
    r = client.post("/skill", json=kakao_body("교수님/결석: 내일 몸살나서 못가요"))
    assert r.status_code == 200
    data = r.json()
    assert_valid_kakao(data)
    assert _text(data).startswith("🎯 받는 사람: 교수님  |  📌 상황: 결석·지각·연차")
    assert "✅ 추천" in _text(data)
    assert _labels(data) == ["받는 사람 바꾸기", "상황 바꾸기", "도움말"]


def test_sync_mode_timeout_then_view_result(client, monkeypatch):
    monkeypatch.setenv("SYNC_WAIT_SEC", "0.05")
    monkeypatch.setenv("MOCK_DELAY", "0.3")

    r = client.post("/skill", json=kakao_body("내일 회의 못갈듯"))
    data = r.json()
    assert_valid_kakao(data)
    assert _text(data) == SYNC_TIMEOUT_TEXT
    assert _labels(data) == ["결과 보기"]

    # 바로 누르면 아직 진행 중
    r = client.post("/skill", json=kakao_body("결과 보기"))
    assert "아직 다듬는 중" in _text(r.json())
    assert _labels(r.json()) == ["결과 보기"]

    time.sleep(0.5)
    r = client.post("/skill", json=kakao_body("결과 보기"))
    data = r.json()
    assert_valid_kakao(data)
    assert _text(data).startswith("🎯 받는 사람: 상사  |  📌 상황: 일반")
    assert "✅ 추천" in _text(data)


def test_callback_mode_posts_result(client):
    with respx.mock(assert_all_called=True) as mock:
        route = mock.post(CALLBACK_URL).mock(return_value=httpx.Response(200, json={}))

        r = client.post(
            "/skill", json=kakao_body("상사/조의: 부친상 들었어요", callback_url=CALLBACK_URL)
        )
        assert r.status_code == 200
        assert r.json() == {
            "version": "2.0",
            "useCallback": True,
            "data": {"text": CALLBACK_ACK_TEXT},
        }

        assert _wait_until(lambda: route.called)
        sent = json.loads(route.calls.last.request.content)
        assert_valid_kakao(sent)
        assert _text(sent).startswith("🎯 받는 사람: 상사  |  📌 상황: 조의(부고)")
        assert _labels(sent) == ["받는 사람 바꾸기", "상황 바꾸기", "도움말"]
        assert route.call_count == 1

    # 콜백으로 보낸 결과도 '결과 보기'로 다시 볼 수 있다
    r = client.post("/skill", json=kakao_body("결과 보기"))
    assert "조의(부고)" in _text(r.json())


def test_callback_failure_does_not_retry_or_crash(client):
    with respx.mock as mock:
        route = mock.post(CALLBACK_URL).mock(return_value=httpx.Response(500))
        r = client.post("/skill", json=kakao_body("안녕하세요", callback_url=CALLBACK_URL))
        assert r.json()["useCallback"] is True
        assert _wait_until(lambda: route.called)
        time.sleep(0.1)
        assert route.call_count == 1

    r = client.post("/skill", json=kakao_body("도움말"))
    assert r.status_code == 200


def test_callback_network_error_is_swallowed(client):
    with respx.mock as mock:
        route = mock.post(CALLBACK_URL).mock(side_effect=httpx.ConnectError("down"))
        client.post("/skill", json=kakao_body("안녕하세요", callback_url=CALLBACK_URL))
        assert _wait_until(lambda: route.called)

    r = client.post("/skill", json=kakao_body("결과 보기"))
    assert r.status_code == 200
    assert "✅ 추천" in _text(r.json())


def test_llm_exception_returns_guide_message(client, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("API 오류")

    monkeypatch.setattr(llm, "_call_model", boom)
    r = client.post("/skill", json=kakao_body("이거 좀 고쳐줘"))
    assert r.status_code == 200
    assert_valid_kakao(r.json())
    assert _text(r.json()) == llm.ERROR_MESSAGE


def test_unknown_target_label_goes_to_correction(client):
    r = client.post("/skill", json=kakao_body("대상:외계인"))
    assert "✅ 추천" in _text(r.json())
    r = client.post("/skill", json=kakao_body("도움말"))
    assert "받는 사람: 상사" in _text(r.json())


def test_long_input_response_stays_within_limits(client, monkeypatch):
    async def long_output(*args, **kwargs):
        return "가" * 2000

    monkeypatch.setattr(llm, "_call_model", long_output)
    r = client.post("/skill", json=kakao_body("나" * 3000))
    data = r.json()
    assert_valid_kakao(data)
    assert len(_text(data)) == 1000
