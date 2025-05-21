# src/giggityflix_mgmt_peer/models/configuration_model.py
from django.db import models
import json
from typing import Any, Dict, List, Optional, Union


class Configuration(models.Model):
    """Model for storing configuration properties."""

    # Type choices for proper conversion
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

    key = models.CharField(max_length=255, primary_key=True,
                           help_text="Configuration property key")
    value = models.TextField(null=True, blank=True,
                             help_text="Current value of the configuration property")
    default_value = models.TextField(null=True, blank=True,
                                     help_text="Default value if not specified")
    value_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_STRING,
                                  help_text="Type of the configuration value")
    description = models.TextField(null=True, blank=True,
                                   help_text="Description of the configuration property")
    is_env_overridable = models.BooleanField(default=True,
                                             help_text="Whether environment variables can override this configuration")
    env_variable = models.CharField(max_length=255, null=True, blank=True,
                                    help_text="Environment variable name to use for override")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['key']
        verbose_name = 'Configuration'
        verbose_name_plural = 'Configurations'

    def __str__(self):
        return f"{self.key}: {self.value}"

    def get_typed_value(self) -> Any:
        """Get the value converted to its appropriate type."""
        if self.value is None:
            return self.get_typed_default_value()

        return self._convert_value(self.value, self.value_type)

    def get_typed_default_value(self) -> Any:
        """Get the default value converted to its appropriate type."""
        if self.default_value is None:
            return None

        return self._convert_value(self.default_value, self.value_type)

    def set_typed_value(self, value: Any) -> None:
        """Set the value, converting it to string for storage."""
        if value is None:
            self.value = None
            return

        if self.value_type == self.TYPE_STRING:
            self.value = str(value)
        elif self.value_type == self.TYPE_INTEGER:
            self.value = str(int(value))
        elif self.value_type == self.TYPE_FLOAT:
            self.value = str(float(value))
        elif self.value_type == self.TYPE_BOOLEAN:
            self.value = str(bool(value)).lower()
        elif self.value_type == self.TYPE_JSON:
            self.value = json.dumps(value)
        elif self.value_type == self.TYPE_LIST:
            # Convert list to comma-separated string
            if isinstance(value, list):
                self.value = ",".join(str(item) for item in value)
            else:
                self.value = str(value)

    @staticmethod
    def _convert_value(value_str: str, value_type: str) -> Any:
        """Convert string value to the appropriate type."""
        if value_str is None:
            return None

        try:
            if value_type == Configuration.TYPE_STRING:
                return value_str
            elif value_type == Configuration.TYPE_INTEGER:
                return int(value_str)
            elif value_type == Configuration.TYPE_FLOAT:
                return float(value_str)
            elif value_type == Configuration.TYPE_BOOLEAN:
                return value_str.lower() in ('true', 'yes', '1', 't', 'y')
            elif value_type == Configuration.TYPE_JSON:
                return json.loads(value_str)
            elif value_type == Configuration.TYPE_LIST:
                # Handle empty case
                if not value_str:
                    return []
                # Split by comma and strip whitespace
                return [item.strip() for item in value_str.split(',')]
            else:
                return value_str
        except Exception:
            # If conversion fails, return original string
            return value_str