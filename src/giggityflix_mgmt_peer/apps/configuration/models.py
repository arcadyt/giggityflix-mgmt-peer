from django.db import models
from .signals import configuration_changed
import json

class Configuration(models.Model):
    TYPE_STRING = 'string'
    TYPE_INT    = 'integer'
    TYPE_FLOAT  = 'float'
    TYPE_BOOL   = 'boolean'
    TYPE_JSON   = 'json'
    TYPE_LIST   = 'list'
    TYPE_CHOICES = [
        (TYPE_STRING, 'String'),
        (TYPE_INT,    'Integer'),
        (TYPE_FLOAT,  'Float'),
        (TYPE_BOOL,   'Boolean'),
        (TYPE_JSON,   'JSON'),
        (TYPE_LIST,   'List'),
    ]

    key          = models.CharField(max_length=255, primary_key=True)
    value        = models.TextField(blank=True, null=True)
    default      = models.TextField(blank=True, null=True)
    value_type   = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_STRING)
    description  = models.TextField(blank=True, null=True)
    updated_at   = models.DateTimeField(auto_now=True)

    # --- helpers -----------------------------------------------------------
    def cast(self, raw: str | None = None):
        raw = self.value if raw is None else raw
        if raw is None:
            return None
        vt = self.value_type
        if vt == self.TYPE_STRING: return raw
        if vt == self.TYPE_INT:    return int(raw)
        if vt == self.TYPE_FLOAT:  return float(raw)
        if vt == self.TYPE_BOOL:   return raw.lower() in ('1','true','t','yes','y')
        if vt == self.TYPE_JSON:   return json.loads(raw)
        if vt == self.TYPE_LIST:   return [x.strip() for x in raw.split(',') if x]
        return raw

    def set_typed(self, python_value):
        if self.value_type == self.TYPE_JSON:
            self.value = json.dumps(python_value)
        elif self.value_type == self.TYPE_LIST:
            self.value = ",".join(map(str, python_value))
        else:
            self.value = str(python_value)

    # --- save hook fires the signal ---------------------------------------
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        configuration_changed.send(
            sender=self.__class__,
            key=self.key,
            value=self.cast(),
        )

    class Meta:
        app_label = 'configuration'
        ordering  = ['key']
