# CLAUDE.md

카카오톡 말투 교정 챗봇 (카카오 i 오픈빌더 스킬 서버 + Gemini/Claude API, `LLM_PROVIDER`로 선택).
**무엇을 만들지는 `SPEC.md`가 기준이다. 작업 전에 반드시 읽을 것.**

## 규칙
- 언어: 코드 주석·커밋 메시지·README는 한국어. 식별자는 영어.
- 커밋: 작은 단위로, `feat:` / `fix:` / `test:` / `chore:` / `docs:` 접두어.
- 테스트와 CI는 항상 `MOCK_LLM=1`. 실제 API를 호출하는 테스트를 만들지 말 것.
- 비밀값(`GEMINI_API_KEY`, `ANTHROPIC_API_KEY` 등)을 코드, 테스트, 커밋, 로그에 넣지 말 것.
- 사용자 발화 원문은 INFO 이상 로그에 남기지 않는다.
- 카카오 응답 제한: 텍스트 1000자, quickReplies 10개, 라벨 14자, 응답 5초.
- 받는 사람/상황 옵션을 바꿀 때는 `app/prompts.py`만 수정한다.
- SPEC과 다르게 해야 할 이유가 생기면 먼저 질문한다.
- 커밋 메시지와 PR 설명에 Co-Authored-By 줄, "Generated with Claude Code" 문구, Claude-Session 줄 등 Claude 관련 표시를 넣지 않는다.

## 명령어
```bash
pip install -r requirements-dev.txt
ruff check .
MOCK_LLM=1 pytest -q
uvicorn app.main:app --reload --port 8000
```
