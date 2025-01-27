from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from django.apps import apps

app = apps.get_app_config("siweauth")

for model_name, model in app.models.items():
    admin.site.register(model)