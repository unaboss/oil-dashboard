import json
import time
from datetime import datetime, timezone
from config import DATA_DIR

_cache = {}

def _cache_file(key):
    return DATA_DIR / f"_cache_{key}.json"

def get(key):
    if key in _cache:
        entry = _cache[key]
        age = time.time() - entry["fetched_at"]
        is_stale = age > entry["ttl"]
        return entry["data"], entry["last_updated"], entry["next_update"], is_stale

    cf = _cache_file(key)
    if cf.exists():
        try:
            entry = json.loads(cf.read_text())
            _cache[key] = entry
            age = time.time() - entry["fetched_at"]
            is_stale = age > entry["ttl"]
            return entry["data"], entry["last_updated"], entry["next_update"], is_stale
        except Exception:
            pass
    return None, None, None, True

def set(key, data, ttl, last_updated=None, next_update=None):
    now = time.time()
    entry = {
        "data": data,
        "fetched_at": now,
        "ttl": ttl,
        "last_updated": last_updated or datetime.now(timezone.utc).isoformat(),
        "next_update": next_update or "",
    }
    _cache[key] = entry
    try:
        _cache_file(key).write_text(json.dumps(entry, default=str))
    except Exception:
        pass

def invalidate(key):
    _cache.pop(key, None)
    cf = _cache_file(key)
    if cf.exists():
        cf.unlink()
