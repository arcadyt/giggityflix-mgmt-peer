from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from giggityflix_mgmt_peer.config.models import Configuration
from giggityflix_mgmt_peer.config.serializers import (
    ConfigurationSerializer, ConfigurationValueSerializer
)
from giggityflix_mgmt_peer.config.service import config_service


class ConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing configuration properties."""

    queryset = Configuration.objects.all()
    serializer_class = ConfigurationSerializer
    lookup_field = 'key'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Use configuration service to set value
        key = serializer.validated_data['key']
        value = serializer.validated_data.get('value')
        value_type = serializer.validated_data.get('value_type', Configuration.TYPE_STRING)

        # Additional fields to save
        config = Configuration(
            key=key,
            value_type=value_type,
            default_value=serializer.validated_data.get('default_value'),
            description=serializer.validated_data.get('description', ''),
            is_env_overridable=serializer.validated_data.get('is_env_overridable', True),
            env_variable=serializer.validated_data.get('env_variable')
        )

        # Set the value
        config.set_typed_value(value)
        config.save()

        # Return the updated configuration
        serializer = self.get_serializer(config)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Update the instance
        for field in serializer.validated_data:
            if field == 'value':
                instance.set_typed_value(serializer.validated_data['value'])
            else:
                setattr(instance, field, serializer.validated_data[field])

        instance.save()

        # Return the updated configuration
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def value(self, request, key=None):
        """Update just the value of a configuration property."""
        config = get_object_or_404(Configuration, key=key)

        serializer = ConfigurationValueSerializer(
            data=request.data,
            context={'key': key}
        )
        serializer.is_valid(raise_exception=True)

        if 'value' in serializer.validated_data:
            # Use configuration service to set value
            success = config_service.set(key, serializer.validated_data['value'])
            if not success:
                return Response(
                    {"error": "Failed to update configuration value"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Return the updated configuration
        config = get_object_or_404(Configuration, key=key)  # Refresh from DB
        config_serializer = ConfigurationSerializer(config)
        return Response(config_serializer.data)

    @action(detail=False, methods=['get'])
    def values(self, request):
        """Get all configuration values as a dictionary."""
        values = config_service.get_all()
        return Response(values)

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """Refresh configuration from environment variables."""
        config_service.initialize()
        return Response({"status": "Configuration refreshed"})