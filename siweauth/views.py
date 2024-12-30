from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from typing import Any, Dict
from rest_framework import exceptions

import datetime
import pytz
import secrets

from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.settings import api_settings

from siweauth.models import Wallet, Nonce
from siweauth.serializers import SIWETokenObtainPairSerializer

@require_http_methods(["GET"])
def get_nonce(request):
    now = datetime.datetime.now(tz=pytz.UTC)

    for n in Nonce.objects.filter(expiration__lte=datetime.datetime.now(tz=pytz.UTC)):
        n.delete()
    n = Nonce(value=secrets.token_hex(12), expiration=now + datetime.timedelta(hours=3))
    n.save()

    return JsonResponse({"nonce": n.value})

class TokenObtainPairView(TokenObtainPairView):
    serializer_class = SIWETokenObtainPairSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def who_am_i(request):
    return JsonResponse({'message': request.user.address})


