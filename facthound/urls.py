"""
URL configuration for facthound project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("questions/", include("questions.urls")),
    path("auth/", include("siweauth.urls")),
    path("admin/", admin.site.urls),
]