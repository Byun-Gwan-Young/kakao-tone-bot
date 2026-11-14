import time

from app.prompts import DEFAULT_SITUATION, DEFAULT_TARGET, SITUATIONS, TARGETS
from app.state import MemoryStateStore


def test_new_user_gets_defaults():
    store = MemoryStateStore()
    st = store.get("u1")
    assert st.target == DEFAULT_TARGET
    assert st.situation == DEFAULT_SITUATION
    assert st.last_result is None
    assert not st.is_pending


def test_same_user_returns_same_state():
    store = MemoryStateStore()
    store.get("u1").target = "교수님"
    assert store.get("u1").target == "교수님"


def test_expired_entries_are_cleaned():
    store = MemoryStateStore(ttl_sec=10)
    store.get("old").updated = time.time() - 100
    store.get("new")
    assert store.cleanup() == 1
    assert len(store) == 1


def test_option_labels_fit_kakao_button_limit():
    for label in TARGETS:
        assert len(f"대상:{label}") <= 14
    for label in SITUATIONS:
        assert len(f"상황:{label}") <= 14
    assert DEFAULT_TARGET in TARGETS
    assert DEFAULT_SITUATION in SITUATIONS
