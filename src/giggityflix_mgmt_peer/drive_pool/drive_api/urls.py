from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PhysicalDriveViewSet, PartitionViewSet

router = DefaultRouter()
router.register(r'drives', PhysicalDriveViewSet)
router.register(r'partitions', PartitionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
