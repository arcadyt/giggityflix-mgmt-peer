"""ORM models for configuration management."""
from django.db import models
import json

class Configuration(models.Model):
    # --- field declarations unchanged ---
    TYPE_STRING = 'string'
    TYPE_INTEGER = 'integer'
    TYPE_FLOAT = 'float'
    TYPE_BOOLEAN = 'boolean'
    TYPE_JSON = 'json'
    TYPE_LIST = 'list'

    TYPE_CHOICES = [
        (TYPE_STRING, 'String'),
        (TYPE_INTEGER, 'Integer'),
        (TYPE_FLOAT, 'Float'),
        (TYPE_BOOLEAN, 'Boolean'),
        (TYPE_JSON, 'JSON'),
        (TYPE_LIST, 'List'),
    ]

    key = models.CharField(max_length=255, primary_key=True)
    value = models.TextField(null=True, blank=True)
    default_value = models.TextField(null=True, blank=True)
    value_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_STRING)
    description = models.TextField(null=True, blank=True)
    is_env_overridable = models.BooleanField(default=True)
    env_variable = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---------- helpers expected by admin / API ----------

    def get_typed_value(self):
        """Return `value` cast to `value_type`."""
        return self._convert(self.value, self.value_type)

    def set_typed_value(self, new_value):
        """Store *new_value* after casting to string for DB."""
        self.value = self._to_storage(new_value)

    # optional: same for default
    def get_typed_default_value(self):
        return self._convert(self.default_value, self.value_type)

    # ---------- internal conversion utils ----------

    @classmethod
    def _to_storage(cls, value):
        if value is None:
            return None
        vt = cls.TYPE_STRING if not hasattr(cls, 'value_type') else cls.value_type
        if vt == cls.TYPE_STRING:
            return str(value)
        if vt == cls.TYPE_INTEGER:
            return str(int(value))
        if vt == cls.TYPE_FLOAT:
            return str(float(value))
        if vt == cls.TYPE_BOOLEAN:
            return str(bool(value)).lower()
        if vt == cls.TYPE_JSON:
            return json.dumps(value)
        if vt == cls.TYPE_LIST:
            return ",".join(str(v) for v in value) if isinstance(value, (list, tuple)) else str(value)
        return str(value)

    @classmethod
    def _convert(cls, raw, vt):
        if raw is None:
            return None
        try:
            if vt == cls.TYPE_STRING:
                return raw
            if vt == cls.TYPE_INTEGER:
                return int(raw)
            if vt == cls.TYPE_FLOAT:
                return float(raw)
            if vt == cls.TYPE_BOOLEAN:
                return raw.lower() in ('true', 'yes', '1', 't', 'y')
            if vt == cls.TYPE_JSON:
                return json.loads(raw)
            if vt == cls.TYPE_LIST:
                return [] if raw == '' else [p.strip() for p in raw.split(',')]
        except Exception:
            pass  # fall through
        return raw

    class Meta:
        app_label = 'configuration'
        ordering = ['key']
        verbose_name = 'Configuration'
        verbose_name_plural = 'Configurations'

    def __str__(self):
        return f"{self.key}: {self.get_typed_value()}"
