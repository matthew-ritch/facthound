from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from typing import Any, Dict
from eth_account.messages import SignableMessage
from eth_account.datastructures import SignedMessage


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
        token = super().get_token(user)
        return token

    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        authenticate_kwargs = {
            "message": SignableMessage(
                *self.context["request"].POST.getlist("message")
            ),
            "signed_message": SignedMessage(
                *self.context["request"].POST.getlist("signed_message")
            ),
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        self.user = authenticate(**authenticate_kwargs)
        refresh = self.get_token(self.user)
        data = {}

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return data
