from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from typing import Any, Dict
from eth_account.messages import SignableMessage
from eth_account.datastructures import SignedMessage

from siweauth.auth import parse_siwe_message
from siweauth.models import User

class SIWETokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields["message"] = serializers.CharField()
        self.fields["signed_message"] = serializers.CharField()
        del self.fields["password"]
        del self.fields[self.username_field]

    @classmethod
    def get_token(cls, user):
        if user:
            token = super().get_token(user)
        else:
            token=None
        return token

    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        authenticate_kwargs = {
            "message": self.context["request"].data["message"],
            "signed_message": self.context["request"].data["signed_message"]
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        self.user = authenticate(**authenticate_kwargs)
        if self.user is None:
            return None
        refresh = self.get_token(self.user)
        data = {}

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'password', 'email')
        extra_kwargs = {'password': {'write_only': True}}
