"""
Serializers for the Sign-In with Ethereum (SIWE) authentication system.

This module provides serializers for JWT token generation using SIWE authentication
and user registration with traditional credentials.
"""

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from typing import Any, Dict
from eth_account.messages import SignableMessage
from eth_account.datastructures import SignedMessage

from siweauth.auth import parse_siwe_message
from siweauth.models import User

class SIWETokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer for obtaining JWT tokens using Sign-In with Ethereum.
    
    This serializer validates SIWE messages and signatures instead of username/password
    to authenticate users and generate JWT tokens.
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize the serializer with SIWE-specific fields.
        
        Removes standard username and password fields and adds message and signature fields.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields["message"] = serializers.CharField()
        self.fields["signed_message"] = serializers.CharField()
        del self.fields["password"]
        del self.fields[self.username_field]

    @classmethod
    def get_token(cls, user):
        """
        Generate a JWT token for the authenticated user.
        
        Args:
            user: The authenticated user
            
        Returns:
            Token: JWT token for the user, or None if user is None
        """
        if user:
            token = super().get_token(user)
        else:
            token=None
        return token

    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        """
        Validate the SIWE message and signature.
        
        This method authenticates the user using the SIWE backend.
        
        Args:
            attrs: Dictionary containing the message and signed_message
            
        Returns:
            dict: Dictionary containing refresh and access tokens if successful
            
        Note:
            Returns None if authentication fails
        """
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
    """
    Serializer for user registration with traditional credentials.
    
    This serializer handles creating users with username, email, and password.
    """
    class Meta:
        model = User
        fields = ('username', 'password', 'email')
        extra_kwargs = {'password': {'write_only': True}}
