"""DRF ViewSet – lean version, all heavy lifting stays in ConfigurationService."""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Configuration                          # ORM: read-only use
from .serializers import ConfigurationSerializer, ConfigurationValueSerializer
from .services import get_configuration_service            # cache + events

svc = get_configuration_service()                          # singleton

class ConfigurationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    CRUD endpoints:
      • GET    /configurations/              (list)
      • GET    /configurations/<key>/        (retrieve)
      • POST   /configurations/              (create)
      • PUT    /configurations/<key>/        (full update)
      • DELETE /configurations/<key>/        (delete)
      • PATCH  /configurations/<key>/value/  (update only 'value')
      • GET    /configurations/dict/         (all configs as {key: value})
    """
    queryset = Configuration.objects.all()   # safe – service keeps cache fresh
    serializer_class = ConfigurationSerializer
    lookup_field = "key"

    # ---------- write operations delegated to the service ----------
    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        svc.set(**ser.validated_data)        # fires events, updates cache
        return Response(ser.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        key = kwargs[self.lookup_field]
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        svc.set(key=key, **ser.validated_data)
        return Response(ser.data)

    def destroy(self, request, *args, **kwargs):
        key = kwargs[self.lookup_field]
        svc.delete(key)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---------- extras ---------------------------------------------
    @action(detail=True, methods=["patch"])
    def value(self, request, key=None):
        """PATCH only the 'value' field – cheaper for UI inline-edit."""
        ser = ConfigurationValueSerializer(data=request.data, context={"key": key})
        ser.is_valid(raise_exception=True)
        svc.set(key, ser.validated_data["value"])
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def dict(self, request):
        """Return all configs as plain dict {key: typed_value}."""
        return Response(svc.get_all())
