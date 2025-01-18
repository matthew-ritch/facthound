from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

import datetime
import pytz
import secrets
import logging

from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from siweauth.models import User, Nonce
from siweauth.serializers import SIWETokenObtainPairSerializer

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logging.basicConfig(
    filename="facthound.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@require_http_methods(["GET"])
def get_nonce(request):
    now = datetime.datetime.now(tz=pytz.UTC)

    for n in Nonce.objects.filter(expiration__lte=datetime.datetime.now(tz=pytz.UTC)):
        n.delete()
    n = Nonce(value=secrets.token_hex(12), expiration=now + datetime.timedelta(hours=3))
    n.save()
    

    return JsonResponse({"nonce": n.value})


class SIWETokenObtainPairView(TokenObtainPairView):
    serializer_class = SIWETokenObtainPairSerializer


class TokenObtainPairView(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        
        response = super().post(request, *args, **kwargs)
        
        return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def who_am_i(request):
    return JsonResponse({"message": request.user.wallet})
