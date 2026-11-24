# =============================================================================
# services/cache_service.py
# Redis caching service with deterministic multi-factor keying, TTL enforcement,
# and graceful fallback when Redis is unavailable.
# =============================================================================

import json
import hashlib
import logging
import os
from typing import Optional, Any

logger = logging.getLogger(__name__)


def compute_cache_key(
    endpoint: str,
    input_text: str,
    prompt_version: str,
    model_id: str,
    corpus_version: str
) -> str:
    """
    Computes a deterministic, collision-resistant cache key factoring in:
    1. Endpoint / task name
    2. Normalized input text (stripped, normalized whitespace)
    3. Prompt / template version hash
    4. Model identifier (e.g. llama-3.3-70b-versatile)
    5. Knowledge-base / corpus version (so changes in Chroma invalidate cache)
    """
    normalized_input = " ".join(input_text.strip().split())
    composite = f"{endpoint}|{normalized_input}|{prompt_version}|{model_id}|{corpus_version}"
    digest = hashlib.sha256(composite.encode("utf-8")).hexdigest()
    return f"dpdp_cache:{endpoint}:{digest}"


class CacheService:
    def __init__(self, redis_client=None, default_ttl: int = None):
        self.client = redis_client
        self.enabled = os.environ.get("ENABLE_CACHE", "true").lower() in ("true", "1", "yes")
        self.default_ttl = default_ttl or int(os.environ.get("CACHE_TTL_SECONDS", "3600"))

    def get(self, key: str) -> Optional[dict]:
        """
        Retrieve and deserialize cached JSON.
        Returns None on cache miss, if disabled, or on Redis connection error.
        """
        if not self.enabled or self.client is None:
            return None

        try:
            raw = self.client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Cache get error for key '{key}': {e}. Falling back to live computation.")
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Serialize and store data with a TTL.
        Never caches failures, errors, or empty payloads.
        Returns True on success, False otherwise.
        """
        if not self.enabled or self.client is None or value is None:
            return False

        # Do not cache error responses
        if isinstance(value, dict) and "error" in value:
            return False

        try:
            effective_ttl = ttl or self.default_ttl
            payload = json.dumps(value)
            self.client.setex(key, effective_ttl, payload)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key '{key}': {e}. Continuing without caching.")
            return False

    def is_available(self) -> bool:
        """Check if Redis is connected and healthy."""
        if not self.enabled or self.client is None:
            return False
        try:
            return bool(self.client.ping())
        except Exception:
            return False
