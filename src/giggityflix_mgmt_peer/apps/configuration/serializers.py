# giggityflix_mgmt_peer/apps/configuration/serializers.py
# Full, self-contained DTO layer – drop in as-is.
from rest_framework import serializers

# If you kept the simplified layout:
from giggityflix_mgmt_peer.apps.configuration.models import Configuration
# If you kept the old DDD layout, switch the import to:
# from giggityflix_mgmt_peer.apps.configuration.infrastructure.orm import Configuration


class ConfigurationSerializer(serializers.ModelSerializer):
    """Expose the full configuration record, plus typed helpers."""

    typed_value = serializers.SerializerMethodField()
    typed_default_value = serializers.SerializerMethodField()

    class Meta:
        model = Configuration
        fields = (
            "key",
            "value",
            "default",             # rename to default_value if you kept that field
            "value_type",
            "description",
            "is_env_overridable",
            "env_variable",
            "created_at",
            "updated_at",
            "typed_value",
            "typed_default_value",
        )
        read_only_fields = ("created_at", "updated_at", "typed_value", "typed_default_value")

    # ---- helper getters --------------------------------------------------
    def get_typed_value(self, obj):
        return obj.cast()                       # one-liner: model handles casting

    def get_typed_default_value(self, obj):
        return obj.cast(obj.default)

    # ---- validation: ensure value ↔ type match ---------------------------
    def validate(self, data):
        """Fail fast if value cannot be cast to value_type."""
        value      = data.get("value",      getattr(self.instance, "value", None))
        value_type = data.get("value_type", getattr(self.instance, "value_type", None))

        if value_type is not None and value is not None:
            try:
                Configuration(value=value, value_type=value_type).cast()
            except Exception as exc:
                raise serializers.ValidationError(
                    {"value": f"Cannot convert to {value_type}: {exc}"}
                )
        return data


class ConfigurationValueSerializer(serializers.Serializer):
    """Patch-only DTO – update `value` while keeping original type."""

    value = serializers.CharField(allow_null=True, required=False)

    def validate(self, data):
        key   = self.context.get("key")
        value = data.get("value")

        if key is None:                       # should not happen – view sets it
            return data

        try:
            cfg = Configuration.objects.get(pk=key)
            Configuration(value=value, value_type=cfg.value_type).cast()
        except Configuration.DoesNotExist:
            raise serializers.ValidationError({"key": "Configuration key not found"})
        except Exception as exc:
            raise serializers.ValidationError(
                {"value": f"Cannot convert to {cfg.value_type}: {exc}"}
            )

        return data
