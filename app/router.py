"""사용자 발화 → 명령 / 설정 / 교정 분기.

`route()`는 즉시 보낼 응답(`Reply`) 또는 교정 요청(`CorrectionRequest`)을 돌려준다.
실제 교정(LLM 호출)과 5초 제한 처리는 `app.main`이 맡는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.kakao import text_response
from app.prompts import DEFAULT_SITUATION, SITUATIONS, TARGETS, settings_line
from app.state import UserState

CMD_CHANGE_TARGET = "받는 사람 바꾸기"
CMD_CHANGE_SITUATION = "상황 바꾸기"
CMD_HELP = "도움말"
CMD_RESULT = "결과 보기"
HELP_COMMANDS = {"", CMD_HELP, "시작", "처음", "사용법"}

TARGET_PREFIX = "대상:"
SITUATION_PREFIX = "상황:"

MAIN_QR = [CMD_CHANGE_TARGET, CMD_CHANGE_SITUATION, CMD_HELP]
RESULT_QR = [CMD_RESULT]

INLINE_HEAD_MAX = 20

HELP_TEXT = """안녕하세요! 대충 쓴 문장을 받는 사람과 상황에 맞게 다듬어 드려요 ✍️

1) 아래 버튼으로 받는 사람과 상황을 고르고
2) 고칠 문장을 그대로 보내 주세요.

한 줄로 지정할 수도 있어요.
예) 교수님/결석: 내일 몸살나서 수업 못갈거같아요
예) 거래처: 견적서 언제 와요"""

PENDING_TEXT = "아직 다듬는 중이에요… 잠시 후 '결과 보기'를 다시 눌러 주세요."
NO_RESULT_TEXT = "아직 다듬은 문장이 없어요. 고칠 문장을 보내 주세요."


@dataclass(frozen=True)
class Reply:
    """바로 보낼 카카오 응답."""

    response: dict


@dataclass(frozen=True)
class CorrectionRequest:
    """교정할 문장과 적용할 설정."""

    text: str
    target: str
    situation: str


@dataclass(frozen=True)
class InlineSpec:
    target: str | None
    situation: str | None
    body: str


def _label_head(label: str) -> str:
    """라벨에서 `·`, `(` 앞부분. 예: `조의(부고)` → `조의`, `거래처·고객` → `거래처`."""
    for sep in ("·", "("):
        label = label.split(sep, 1)[0]
    return label


def match_label(part: str, labels) -> str | None:
    """part와 일치하는 라벨을 찾는다. 같음 > 앞부분 같음 > 포함 순으로 우선한다."""
    part = "".join(part.split())
    if not part:
        return None
    labels = list(labels)
    for label in labels:
        if part == label:
            return label
    for label in labels:
        if part == _label_head(label):
            return label
    for label in labels:
        if part in label:
            return label
    return None


def parse_inline(utterance: str) -> InlineSpec | None:
    """`<머리>:<본문>` 형식이면 InlineSpec, 아니면 None."""
    if ":" not in utterance:
        return None
    head, body = utterance.split(":", 1)
    head, body = head.strip(), body.strip()
    if not head or len(head) > INLINE_HEAD_MAX or not body:
        return None

    target = situation = None
    for part in head.split("/"):
        if target is None and (found := match_label(part, TARGETS)):
            target = found
        elif situation is None and (found := match_label(part, SITUATIONS)):
            situation = found
    if target is None and situation is None:
        return None
    return InlineSpec(target=target, situation=situation, body=body)


def _current(state: UserState) -> str:
    return settings_line(state.target, state.situation)


def help_reply(state: UserState) -> Reply:
    return Reply(text_response(f"{HELP_TEXT}\n\n현재 설정\n{_current(state)}", MAIN_QR))


def route(utterance: str, state: UserState) -> Reply | CorrectionRequest:
    text = utterance.strip()

    if text in HELP_COMMANDS:
        return help_reply(state)

    if text == CMD_CHANGE_TARGET:
        return Reply(
            text_response(
                "누구에게 보낼 메시지인가요?", [f"{TARGET_PREFIX}{label}" for label in TARGETS]
            )
        )

    if text == CMD_CHANGE_SITUATION:
        return Reply(
            text_response(
                "어떤 상황인가요?", [f"{SITUATION_PREFIX}{label}" for label in SITUATIONS]
            )
        )

    if text.startswith(TARGET_PREFIX):
        label = text[len(TARGET_PREFIX) :].strip()
        if label in TARGETS:
            state.target = label
            return Reply(text_response(f"설정했어요!\n{_current(state)}", MAIN_QR))

    if text.startswith(SITUATION_PREFIX):
        label = text[len(SITUATION_PREFIX) :].strip()
        if label in SITUATIONS:
            state.situation = label
            return Reply(text_response(f"설정했어요!\n{_current(state)}", MAIN_QR))

    if text == CMD_RESULT:
        if state.is_pending:
            return Reply(text_response(PENDING_TEXT, RESULT_QR))
        if state.last_result:
            return Reply(text_response(state.last_result, MAIN_QR))
        return Reply(text_response(NO_RESULT_TEXT, MAIN_QR))

    # 그 외: 문장 교정. 한 줄 지정이면 설정을 저장하고 본문만 교정한다.
    body = text
    inline = parse_inline(text)
    if inline is not None:
        body = inline.body
        if inline.target is not None:
            state.target = inline.target
            if inline.situation is None:
                # 안전 규칙: 받는 사람만 지정하면 상황을 일반으로 초기화
                state.situation = DEFAULT_SITUATION
        if inline.situation is not None:
            state.situation = inline.situation

    return CorrectionRequest(text=body, target=state.target, situation=state.situation)
