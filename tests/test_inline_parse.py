"""한 줄 지정(인라인) 파싱 검증 (SPEC 7-3)."""

import pytest

from app.prompts import SITUATIONS, TARGETS
from app.router import InlineSpec, match_label, parse_inline


def test_target_and_situation():
    spec = parse_inline("교수님/결석: 저 내일 몸살나서 수업 못갈거같아요")
    assert spec == InlineSpec(
        target="교수님", situation="결석·지각·연차", body="저 내일 몸살나서 수업 못갈거같아요"
    )


def test_situation_only():
    spec = parse_inline("조의: 삼가 고인의 명복을 빕니다")
    assert spec == InlineSpec(target=None, situation="조의(부고)", body="삼가 고인의 명복을 빕니다")


def test_target_only_by_prefix():
    spec = parse_inline("거래처: 견적서 언제 와요")
    assert spec == InlineSpec(target="거래처·고객", situation=None, body="견적서 언제 와요")


def test_order_does_not_matter():
    spec = parse_inline("조의/상사: 부친상 소식 들었습니다")
    assert spec is not None
    assert spec.target == "상사"
    assert spec.situation == "조의(부고)"


def test_spaces_in_head_are_ignored():
    spec = parse_inline(" 교 수 님 / 축 하 : 합격했어요")
    assert spec is not None
    assert spec.target == "교수님"
    assert spec.situation == "축하(경사)"


def test_unmatched_head_is_not_inline():
    assert parse_inline("참고: 회의 3시") is None


def test_head_over_20_chars_is_not_inline():
    head = "교수님" + "가" * 18  # 21자
    assert len(head) > 20
    assert parse_inline(f"{head}: 본문") is None


def test_head_exactly_20_chars_still_allowed():
    head = "교수님/" + " " * 16  # 공백 포함 20자
    assert len(head) == 20
    assert parse_inline(f"{head}: 본문") is not None


@pytest.mark.parametrize("utt", ["교수님:", "교수님:   ", "교수님/결석:"])
def test_empty_body_is_not_inline(utt):
    assert parse_inline(utt) is None


def test_no_colon_is_not_inline():
    assert parse_inline("교수님 내일 결석합니다") is None


def test_body_may_contain_colon():
    spec = parse_inline("상사/보고: 회의 시간: 3시")
    assert spec is not None
    assert spec.body == "회의 시간: 3시"


@pytest.mark.parametrize(
    "part, expected",
    [
        ("조의", "조의(부고)"),
        ("결석", "결석·지각·연차"),
        ("축하(경사)", "축하(경사)"),
        ("지각", "결석·지각·연차"),
    ],
)
def test_match_situation(part, expected):
    assert match_label(part, SITUATIONS) == expected


@pytest.mark.parametrize(
    "part, expected", [("거래처", "거래처·고객"), ("고객", "거래처·고객"), ("어른", "어른·친척")]
)
def test_match_target(part, expected):
    assert match_label(part, TARGETS) == expected


def test_empty_part_matches_nothing():
    assert match_label("  ", TARGETS) is None
