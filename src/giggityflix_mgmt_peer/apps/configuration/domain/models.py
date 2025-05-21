"""Domain models for configuration management."""
import json
from typing import Any, Optional


class ConfigurationValue:
    """Value object representing a configuration setting."""

    TYPE_STRING = 'string'
    TYPE_INTEGER = 'integer'
    TYPE_FLOAT = 'float'
    TYPE_BOOLEAN = 'boolean'
    TYPE_JSON = 'json'
    TYPE_LIST = 'list'

    TYPE_CHOICES = [
        TYPE_STRING, TYPE_INTEGER, TYPE_FLOAT,
        TYPE_BOOLEAN, TYPE_JSON, TYPE_LIST
    ]

    def __init__(
            self,
            key: str,
            value: Any = None,
            default_value: Any = None,
            value_type: str = TYPE_STRING,
            description: str = "",
            is_env_overridable: bool = True,
            env_variable: Optional[str] = None
    ):
        self.key = key
        self._value = value
        self._default_value = default_value
        self.value_type = value_type
        self.description = description
        self.is_env_overridable = is_env_overridable
        self.env_variable = env_variable

    @property
    def value(self) -> Any:
        """Get the typed value, falling back to default if not set."""
        if self._value is None:
            return self.default_value
        return self._convert_value(self._value, self.value_type)

    @value.setter
    def value(self, new_value: Any) -> None:
        """Set the value, converting to string for storage."""
        self._value = self._to_storage_format(new_value)

    @property
    def default_value(self) -> Any:
        """Get the typed default value."""
        if self._default_value is None:
            return None
        return self._convert_value(self._default_value, self.value_type)

    @default_value.setter
    def default_value(self, new_value: Any) -> None:
        """Set the default value, converting to string for storage."""
        self._default_value = self._to_storage_format(new_value)

    def _to_storage_format(self, value: Any) -> str:
        """Convert any value to string format for storage."""
        if value is None:
            return None

        if self.value_type == self.TYPE_STRING:
            return str(value)
        elif self.value_type == self.TYPE_INTEGER:
            return str(int(value))
        elif self.value_type == self.TYPE_FLOAT:
            return str(float(value))
        elif self.value_type == self.TYPE_BOOLEAN:
            return str(bool(value)).lower()
        elif self.value_type == self.TYPE_JSON:
            return json.dumps(value)
        elif self.value_type == self.TYPE_LIST:
            if isinstance(value, list):
                return ",".join(str(item) for item in value)
            return str(value)
        return str(value)

    @staticmethod
    def _convert_value(value_str: str, value_type: str) -> Any:
        """Convert string value to the appropriate type."""
        if value_str is None:
            return None

        try:
            if value_type == ConfigurationValue.TYPE_STRING:
                return value_str
            elif value_type == ConfigurationValue.TYPE_INTEGER:
                return int(value_str)
            elif value_type == ConfigurationValue.TYPE_FLOAT:
                return float(value_str)
            elif value_type == ConfigurationValue.TYPE_BOOLEAN:
                return value_str.lower() in ('true', 'yes', '1', 't', 'y')
            elif value_type == ConfigurationValue.TYPE_JSON:
                return json.loads(value_str)
            elif value_type == ConfigurationValue.TYPE_LIST:
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


class ConfigurationChangeEvent:
    """Event object representing a configuration change."""

    def __init__(self, key: str, old_value: Any, new_value: Any, value_type: str):
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.value_type = value_type
        self.timestamp = None  # Will be set when fired
