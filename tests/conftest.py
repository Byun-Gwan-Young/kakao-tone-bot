"""테스트 공통 설정. 실제 API를 절대 호출하지 않도록 mock 모드를 강제한다."""

import os

os.environ["MOCK_LLM"] = "1"
os.environ.setdefault("MOCK_DELAY", "0.01")
