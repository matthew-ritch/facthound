from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from typing import Any, Dict
from rest_framework.settings import api_settings
from eth_account.messages import SignableMessage
from eth_account.datastructures import SignedMessage

class SIWETokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields["message"] = serializers.CharField()
        self.fields["signed_message"] = serializers.CharField()
        del self.fields['password']
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        return token
    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        authenticate_kwargs = {
            "message": SignableMessage(*self.context["request"].POST.getlist('message')),
            "signed_message": SignedMessage(*self.context["request"].POST.getlist('signed_message')),
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        self.user = authenticate(**authenticate_kwargs)

        return {}