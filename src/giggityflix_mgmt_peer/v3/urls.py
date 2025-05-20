from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('giggityflix_mgmt_peer.v3.drive_pool.drive_api.urls')),
]