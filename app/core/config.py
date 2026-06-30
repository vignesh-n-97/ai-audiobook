"""
API-specific config.

Re-exports shared Config so routers only need to import from app.core.config.
Extend here with API-specific settings if needed (e.g. JWT secrets).
"""

from __future__ import annotations

from functools import lru_cache

from app.shared.config import Config


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return the singleton Config instance.

    Cached after first call — safe for use with FastAPI's Depends().
    """
    return Config()
