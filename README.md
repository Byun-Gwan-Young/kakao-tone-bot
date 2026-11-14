# kakao-tone-bot

카카오톡 채널 챗봇에 대충 쓴 문장을 보내면, 미리 고른 **받는 사람**(상사, 교수님 등)과 **상황**(조의, 축하, 결석 연락 등)에 맞춰 바로 보낼 수 있는 문장으로 다듬어 주는 챗봇입니다.
카카오 i 오픈빌더 **스킬 서버**(FastAPI)와 LLM API로 동작합니다. 기본은 **Google Gemini**(무료 요금제 사용 가능)이고, 설정 하나로 **Claude**로 바꿀 수 있습니다.

```
👤 교수님/결석: 교수님 저 내일 몸살나서 수업 못갈거같아요 과제는 메일로 낼게요
🤖 🎯 받는 사람: 교수님  |  📌 상황: 결석·지각·연차

   ✅ 추천
   교수님, 안녕하세요. [학과] [이름]입니다. ...

   🌿 조금 더 부드럽게
   ...

   💡 한 줄 팁
   ...
   [받는 사람 바꾸기] [상황 바꾸기] [도움말]
```

## 사용법 (챗봇에서)

| 보내는 말 | 동작 |
|---|---|
| `도움말`, `시작`, `처음`, `사용법` | 사용법과 현재 설정 |
| `받는 사람 바꾸기` / `상황 바꾸기` | 선택 버튼 표시 |
| `대상:교수님`, `상황:조의(부고)` | 설정 저장 (버튼을 누르면 자동 전송) |
| `교수님/결석: 내일 못가요` | 한 줄로 받는 사람·상황 지정 + 교정 (설정도 저장) |
| `결과 보기` | 시간이 오래 걸린 교정 결과 확인 |
| 그 밖의 문장 | 현재 설정으로 교정 |

- 한 줄 지정은 줄임말도 됩니다: `조의` → `조의(부고)`, `거래처` → `거래처·고객`, `결석` → `결석·지각·연차`
- 받는 사람만 지정하면(`거래처: ...`) 상황은 `일반`으로 초기화됩니다.
- 받는 사람/상황 목록은 `app/prompts.py`에서 바꿀 수 있습니다.

## 로컬 실행

Python 3.11 이상이 필요합니다.

```bash
pip install -r requirements-dev.txt
```

```bash
cp .env.example .env
```

Windows cmd에서는 `copy .env.example .env`를 씁니다.

`.env`에 `GEMINI_API_KEY`를 넣습니다. (`.env`는 커밋되지 않습니다.) 키 없이 동작만 확인하려면 `MOCK_LLM=1`로 두면 가짜 응답이 나옵니다.

### Gemini API 키 발급 (무료)

1. [Google AI Studio](https://aistudio.google.com)에 Google 계정으로 로그인합니다.
2. **Get API key** → **Create API key**로 키를 만듭니다.
3. 키를 `.env`의 `GEMINI_API_KEY=` 뒤에 붙여 넣습니다. 채팅이나 코드에는 절대 넣지 마세요.

무료 요금제 주의사항:
- 분당·하루 요청 수 한도가 있고, **모든 사용자가 키 하나의 한도를 함께 씁니다.** 한도를 넘으면 사용자에게 "잠시 후 다시 보내 주세요" 안내가 나갑니다. 현재 한도는 AI Studio에서 확인하세요.
- 무료 요금제는 **입력 내용이 Google 제품 개선에 쓰일 수 있습니다.** 아래 카카오 설정 8번처럼 채널 소개에 꼭 알려 주세요. 결제를 연결한 유료 요금제는 그렇지 않습니다.
- 기본 모델은 `gemini-3.8-flash`입니다. Google이 모델을 바꾸거나 종료하면 AI Studio에서 무료로 쓸 수 있는 Flash 모델 이름을 확인해 `GEMINI_MODEL`에 넣으세요.

### Claude로 바꾸기

`.env`에서 `LLM_PROVIDER=anthropic`으로 바꾸고 `ANTHROPIC_API_KEY`를 넣으면 됩니다. 코드 수정은 필요 없습니다.

```bash
uvicorn app.main:app --reload --port 8000 --env-file .env
```

`--env-file .env`가 `.env`의 값을 읽어 줍니다. Windows(cmd, PowerShell)에서도 똑같이 쓸 수 있습니다.

동작 확인:

```bash
curl -s localhost:8000/skill -H 'content-type: application/json' -d '{"userRequest":{"utterance":"교수님/결석: 내일 몸살나서 수업 못갈거같아요","user":{"id":"me"}}}'
```

브라우저에서 http://localhost:8000/docs 를 열면 `/skill`을 직접 눌러 볼 수도 있습니다.

실제 API로 예시 문장 5개를 돌려 보려면 다음을 실행합니다. `.env`를 자동으로 읽습니다.

```bash
python scripts/try_real.py
```

### 외부에서 접속되게 하기 (ngrok)

카카오 서버가 내 PC에 접속할 수 있도록 [ngrok](https://ngrok.com/)으로 터널을 엽니다.

```bash
ngrok http 8000
```

출력된 `https://xxxx.ngrok-free.app` 주소에 `/skill`을 붙인 `https://xxxx.ngrok-free.app/skill`을 아래 오픈빌더 스킬 URL로 씁니다. (ngrok 무료 주소는 실행할 때마다 바뀌므로 바뀌면 스킬 URL도 고쳐야 합니다.)

## 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini` 또는 `anthropic` |
| `GEMINI_API_KEY` | (없음) | Gemini 사용 시 필수. 없으면 시작 시 경고 로그 |
| `GEMINI_MODEL` | `gemini-3.8-flash` | 사용할 Gemini 모델 |
| `GEMINI_THINKING_LEVEL` | `LOW` | Gemini 3 이상의 생각 정도 (`MINIMAL`/`LOW`/`MEDIUM`/`HIGH`). 낮을수록 빠름. 모델마다 지원하는 값이 다름 (`gemini-3.8-flash`는 `MINIMAL` 미지원) |
| `ANTHROPIC_API_KEY` | (없음) | Claude 사용 시 필수 |
| `CLAUDE_MODEL` | `claude-haiku-5-5` | 사용할 Claude 모델 |
| `SYNC_WAIT_SEC` | `4.0` | 동기 모드에서 결과를 기다리는 시간(초) |
| `MOCK_LLM` | `0` | `1`이면 API를 부르지 않고 가짜 응답 |
| `MOCK_DELAY` | `0.2` | 가짜 응답 지연(초) |
| `LOG_LEVEL` | `INFO` | 사용자 문장 원문은 `DEBUG`에서만 로그에 남습니다 |

## 상시 운영 (Render 또는 Railway)

저장소에 `Dockerfile`이 있으므로 두 서비스 모두 그대로 배포됩니다.

**Render**
1. render.com → New → Web Service → 이 GitHub 저장소 연결
2. Runtime은 Docker 선택 (자동 인식)
3. Environment에 `GEMINI_API_KEY` 추가 (Claude를 쓰면 `LLM_PROVIDER=anthropic`과 `ANTHROPIC_API_KEY`)
4. 배포가 끝나면 `https://<서비스명>.onrender.com/skill`을 스킬 URL로 사용

**Railway**
1. railway.app → New Project → Deploy from GitHub repo → 이 저장소 선택
2. Variables에 `GEMINI_API_KEY` 추가
3. Settings → Networking → Generate Domain
4. `https://<도메인>/skill`을 스킬 URL로 사용

> 무료 플랜은 한동안 요청이 없으면 서버가 잠들어 첫 응답이 5초를 넘을 수 있습니다. 사용자 설정은 메모리에 저장되므로 서버가 재시작되면 초기화됩니다.

## 카카오 설정 순서

1. [카카오톡 채널 관리자센터](https://center-pf.kakao.com)에서 채널을 만듭니다.
2. [카카오 i 오픈빌더](https://chatbot.kakao.com)에서 봇을 만들고 위 채널을 연결합니다.
3. **스킬** 메뉴에서 스킬을 추가하고 URL에 `https://<서버>/skill`을 넣습니다.
4. **폴백 블록**을 열어 위 스킬을 연결하고, 응답을 **"스킬 데이터 사용"**으로 지정합니다. (모든 발화가 서버로 오게 됩니다.)
5. (선택) **웰컴 블록**도 같은 스킬로 연결하면 처음 들어온 사용자에게 도움말이 나갑니다.
6. 배포한 뒤 실제 채널에서 메시지를 보내 테스트합니다.
7. (선택) 설정 → AI 챗봇 관리에서 **'AI 챗봇 전환'(콜백)**을 신청합니다. 승인되면 폴백 블록에서 콜백을 켭니다. 코드 수정은 필요 없습니다. 콜백은 봇 테스트 창에서 완전히 지원되지 않으니 배포 후 실제 채널에서 확인하세요.
8. **개인정보 안내**: 사용자가 보낸 문장이 교정을 위해 외부 AI API(Google Gemini, 또는 Claude를 쓰면 Anthropic)로 전송된다는 점을 채널 소개에 적어 두세요. Gemini 무료 요금제를 쓴다면 입력 내용이 Google 제품 개선에 쓰일 수 있다는 점도 함께 적어 주세요.

### 5초 제한 처리

카카오는 스킬 응답을 5초 안에 받아야 합니다.

- **콜백 모드** (요청에 `callbackUrl`이 있을 때): 즉시 "말투 다듬는 중이에요 ✍️ 잠시만요!"를 보내고, 교정이 끝나면 결과를 `callbackUrl`로 전송합니다.
- **동기 모드** (콜백이 꺼져 있을 때): `SYNC_WAIT_SEC`(기본 4초)까지 기다렸다가, 넘기면 `[결과 보기]` 버튼을 안내합니다. 교정은 계속 진행되고 버튼을 누르면 결과가 나옵니다.

## 개발

```bash
ruff check .
```

```bash
MOCK_LLM=1 pytest -q
```

테스트와 CI는 항상 `MOCK_LLM=1`로 실행하며 실제 API를 호출하지 않습니다.

```
app/
  main.py     FastAPI 앱, /skill, / (헬스체크), 동기/콜백 모드
  kakao.py    카카오 요청 파싱 + 응답 JSON 생성
  router.py   발화 → 명령/설정/교정 분기, 한 줄 지정 파싱
  llm.py      LLM 호출: Gemini/Claude (mock 모드, 오류 처리)
  prompts.py  받는 사람/상황 목록, 시스템 프롬프트
  state.py    사용자별 설정 저장소 (메모리 구현, 24시간 지나면 정리)
  config.py   환경변수 로딩
```
