"""
URL configuration for facthound project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/questions/", include("questions.urls")),
    path("api/auth/", include("siweauth.urls")),
    path("api/admin/", admin.site.urls),
]