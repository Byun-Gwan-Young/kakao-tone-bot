"""카카오 i 오픈빌더 스킬 요청 파싱과 응답 JSON 생성.

응답 제한: 텍스트 1000자, quickReplies 10개, 라벨 14자.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

MAX_TEXT_LEN = 1000
MAX_QUICK_REPLIES = 10
MAX_LABEL_LEN = 14
ANONYMOUS_USER = "anonymous"


@dataclass(frozen=True)
class KakaoRequest:
    utterance: str
    user_id: str
    callback_url: str | None


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def parse_request(body: Any) -> KakaoRequest:
    """스킬 요청 본문에서 필요한 필드만 꺼낸다. 형식이 이상해도 예외를 던지지 않는다."""
    user_request = _as_dict(_as_dict(body).get("userRequest"))
    user = _as_dict(user_request.get("user"))

    utterance = user_request.get("utterance")
    utterance = utterance.strip() if isinstance(utterance, str) else ""

    user_id = user.get("id")
    user_id = str(user_id) if isinstance(user_id, (str, int)) and str(user_id) else ANONYMOUS_USER

    callback_url = user_request.get("callbackUrl")
    if not isinstance(callback_url, str) or not callback_url.strip():
        callback_url = None

    return KakaoRequest(utterance=utterance, user_id=user_id, callback_url=callback_url)


def truncate_text(text: str, limit: int = MAX_TEXT_LEN) -> str:
    """limit자를 넘으면 (limit-1)자 + `…`로 자른다."""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def quick_replies(labels: Iterable[str]) -> list[dict]:
    """버튼 라벨 목록을 quickReplies로 만든다. 최대 10개, 라벨은 14자로 자른다.

    누르면 원래 라벨 전체가 발화로 전송된다.
    """
    result = []
    for label in list(labels)[:MAX_QUICK_REPLIES]:
        result.append(
            {
                "label": label[:MAX_LABEL_LEN],
                "action": "message",
                "messageText": label,
            }
        )
    return result


def text_response(text: str, buttons: Iterable[str] | None = None) -> dict:
    """simpleText 하나와 (선택) quickReplies로 이루어진 스킬 응답."""
    template: dict[str, Any] = {"outputs": [{"simpleText": {"text": truncate_text(text)}}]}
    replies = quick_replies(buttons or [])
    if replies:
        template["quickReplies"] = replies
    return {"version": "2.0", "template": template}


def callback_ack_response(text: str) -> dict:
    """콜백 모드에서 즉시 돌려주는 응답."""
    return {"version": "2.0", "useCallback": True, "data": {"text": text}}
