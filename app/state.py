"""사용자별 설정 저장소.

`StateStore` 인터페이스를 두어 나중에 Redis 등으로 바꿔 끼울 수 있게 한다.
지금은 메모리 구현(`MemoryStateStore`)만 제공한다.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.prompts import DEFAULT_SITUATION, DEFAULT_TARGET

STATE_TTL_SEC = 24 * 60 * 60  # 24시간 동안 활동이 없으면 정리
CLEANUP_INTERVAL_SEC = 60.0  # 정리는 최대 1분에 한 번만 가볍게


@dataclass
class UserState:
    target: str = DEFAULT_TARGET
    situation: str = DEFAULT_SITUATION
    pending: asyncio.Task | None = None  # 진행 중인 교정 태스크
    last_result: str | None = None  # 가장 최근 교정 결과
    updated: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.updated = time.time()

    @property
    def is_pending(self) -> bool:
        return self.pending is not None and not self.pending.done()


class StateStore(ABC):
    @abstractmethod
    def get(self, user_id: str) -> UserState:
        """사용자 상태를 돌려준다. 없으면 기본값으로 새로 만든다."""


class MemoryStateStore(StateStore):
    def __init__(
        self,
        ttl_sec: float = STATE_TTL_SEC,
        cleanup_interval_sec: float = CLEANUP_INTERVAL_SEC,
    ) -> None:
        self._data: dict[str, UserState] = {}
        self._ttl = ttl_sec
        self._cleanup_interval = cleanup_interval_sec
        self._last_cleanup = 0.0

    def get(self, user_id: str) -> UserState:
        now = time.time()
        if now - self._last_cleanup >= self._cleanup_interval:
            self.cleanup(now)
        state = self._data.get(user_id)
        if state is None:
            state = UserState()
            self._data[user_id] = state
        state.touch()
        return state

    def cleanup(self, now: float | None = None) -> int:
        """`updated` 기준 TTL이 지난 항목을 지우고 지운 개수를 돌려준다."""
        now = time.time() if now is None else now
        self._last_cleanup = now
        expired = [
            uid
            for uid, st in self._data.items()
            if now - st.updated > self._ttl and not st.is_pending
        ]
        for uid in expired:
            del self._data[uid]
        return len(expired)

    def __len__(self) -> int:
        return len(self._data)
