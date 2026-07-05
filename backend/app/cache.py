"""Tiny thread-safe in-memory TTL cache (replaces Streamlit's st.cache_data)."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            hit = self._store.get(key)
            if not hit:
                return None
            expires_at, value = hit
            if expires_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        with self._lock:
            self._store[key] = (time.time() + ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


_cache = TTLCache()


def cached(ttl: float, prefix: str):
    """Decorator caching a function's return value by its positional args."""

    def decorator(fn: Callable):
        def wrapper(*args, **kwargs):
            key = f"{prefix}:{args}:{sorted(kwargs.items())}"
            cached_value = _cache.get(key)
            if cached_value is not None:
                return cached_value
            result = fn(*args, **kwargs)
            if result is not None:
                _cache.set(key, result, ttl)
            return result

        return wrapper

    return decorator
