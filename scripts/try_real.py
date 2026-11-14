"""실제 LLM API로 예시 문장 5개를 교정해 출력 형식을 눈으로 확인하는 스크립트.

사용법 (저장소 루트에서, .env 또는 환경변수에 키를 넣은 뒤. .env는 자동으로 읽는다):
    GEMINI_API_KEY=... python scripts/try_real.py
    LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... python scripts/try_real.py

테스트/CI에서는 실행하지 않는다. 실제 API를 호출하므로 비용이나 무료 한도가 쓰인다.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:  # uvicorn[standard]에 포함된 python-dotenv로 .env를 읽는다 (이미 설정된 값은 유지)
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from app import llm  # noqa: E402
from app.config import get_settings  # noqa: E402

EXAMPLES = [
    ("교수님", "결석·지각·연차", "교수님 저 내일 몸살나서 수업 못갈거같아요 과제는 메일로 낼게요"),
    ("상사", "조의(부고)", "팀장님 부친상 소식 들었어요 너무 놀랐어요 ㅠㅠ 힘내세요!!"),
    ("거래처·고객", "부탁·요청", "견적서 언제 와요? 이번주 안에 꼭 주세요"),
    ("친구", "축하(경사)", "야 결혼 축하해 진짜 대박이다"),
    ("선배", "감사", "어제 밥 사주셔서 감사해요 덕분에 잘 먹었어요"),
]


async def main() -> int:
    if os.getenv("MOCK_LLM") == "1":
        print("MOCK_LLM=1 이면 실제 API를 호출하지 않습니다. MOCK_LLM을 끄고 실행하세요.")
        return 1
    settings = get_settings()
    if not settings.api_key:
        print(f"{settings.api_key_name}가 없습니다. 키를 설정한 뒤 실행하세요.")
        return 1
    print(f"LLM 제공자: {settings.llm_provider}")

    for target, situation, text in EXAMPLES:
        print("=" * 60)
        print(f"[원문] {target}/{situation}: {text}\n")
        result = await llm.correct(text, target, situation)
        print(result)
        print(f"\n({len(result)}자)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
