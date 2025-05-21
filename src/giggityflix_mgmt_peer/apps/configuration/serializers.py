"""Serializers for configuration models."""
from rest_framework import serializers

from giggityflix_mgmt_peer.apps.configuration.infrastructure.orm import Configuration


class ConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for Configuration model."""

    typed_value = serializers.SerializerMethodField()
    typed_default_value = serializers.SerializerMethodField()

    class Meta:
        model = Configuration
        fields = [
            'key', 'value', 'default_value', 'value_type', 'description',
            'is_env_overridable', 'env_variable', 'created_at', 'updated_at',
            'typed_value', 'typed_default_value'
        ]
        read_only_fields = ['created_at', 'updated_at', 'typed_value', 'typed_default_value']

    def get_typed_value(self, obj):
        """Get the typed value of the configuration."""
        return obj.get_typed_value()

    def get_typed_default_value(self, obj):
        """Get the typed default value of the configuration."""
        return obj.get_typed_default_value()

    def validate(self, data):
        """Validate that the value can be converted to the specified type."""
        if 'value' in data and 'value_type' in data:
            # Create a temporary configuration object to test type conversion
            temp_config = Configuration(
                value=data['value'],
                value_type=data['value_type']
            )
            try:
                temp_config.get_typed_value()
            except Exception as e:
                raise serializers.ValidationError(
                    f"Cannot convert value to type {data['value_type']}: {str(e)}"
                )

        return data


class ConfigurationValueSerializer(serializers.Serializer):
    """Serializer for updating just the value of a configuration property."""

    value = serializers.CharField(allow_null=True, required=False)

    def validate(self, data):
        """Ensure the value can be converted to the configuration's type."""
        value = data.get('value')

        if 'key' in self.context:
            key = self.context['key']
            try:
                config = Configuration.objects.get(key=key)

                # Create a temporary configuration to test type conversion
                temp_config = Configuration(
                    value=value,
                    value_type=config.value_type
                )
                try:
                    temp_config.get_typed_value()
                except Exception as e:
                    raise serializers.ValidationError(
                        f"Cannot convert value to type {config.value_type}: {str(e)}"
                    )
            except Configuration.DoesNotExist:
                pass  # This will be handled by the view

        return data
