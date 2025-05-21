from functools import lru_cache
from .models import Configuration
from .signals import configuration_changed

_CACHE = {}

def get(key, default=None):
    if key in _CACHE:
        return _CACHE[key]
    try:
        cfg = Configuration.objects.get(pk=key)
        _CACHE[key] = cfg.cast()
        return _CACHE[key]
    except Configuration.DoesNotExist:
        return default

def set(key, value, value_type=None):
    cfg, _ = Configuration.objects.get_or_create(pk=key)
    if value_type:                 # optional overwrite
        cfg.value_type = value_type
    cfg.set_typed(value)
    cfg.save()                     # fires signal, cache auto-clears via receiver
