"""
Authentication views for Sign-In with Ethereum (SIWE).

This module provides API endpoints for Ethereum wallet authentication using SIWE,
including nonce generation, token obtaining, and user management.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response

import datetime
import pytz
import secrets
import logging

from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from siweauth.models import User, Nonce
from siweauth.serializers import SIWETokenObtainPairSerializer, UserSerializer


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
    """
    Generate and return a new nonce for SIWE authentication.
    
    Endpoint: GET /api/auth/nonce/
    
    This function creates a new nonce with a 3-hour expiration and returns it.
    It also cleans up expired nonces from the database.
    
    Args:
        request: HTTP request
        
    Returns:
        JsonResponse: A JSON response containing the generated nonce
    """
    now = datetime.datetime.now(tz=pytz.UTC)

    for n in Nonce.objects.filter(expiration__lte=datetime.datetime.now(tz=pytz.UTC)):
        n.delete()
    n = Nonce(value=secrets.token_hex(12), expiration=now + datetime.timedelta(hours=3))
    n.save()

    return JsonResponse({"nonce": n.value})


class SIWETokenObtainPairView(TokenObtainPairView):
    """
    API endpoint for obtaining JWT tokens using Sign-In with Ethereum.
    
    This view extends TokenObtainPairView to use SIWE authentication
    instead of traditional username/password authentication.
    """
    serializer_class = SIWETokenObtainPairSerializer


class TokenObtainPairView(TokenObtainPairView):
    """
    API endpoint for obtaining JWT tokens using traditional authentication.
    
    This view provides standard JWT token authentication using username/password.
    """
    serializer_class = TokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """
        Process a token request with additional logging.
        
        Args:
            request: HTTP request with authentication credentials
            
        Returns:
            Response: Response with token pair if authentication succeeds
        """
        response = super().post(request, *args, **kwargs)

        return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def who_am_i(request):
    """
    Return the wallet address of the authenticated user. Used for debugging.
    
    Endpoint: GET /api/auth/whoami/
    
    Args:
        request: HTTP request from authenticated user
        
    Returns:
        JsonResponse: The wallet address of the authenticated user
        
    Permission:
        Requires authentication
    """
    return JsonResponse({"message": request.user.wallet})


class CreateUserView(generics.CreateAPIView):
    """
    API endpoint for creating new users.
    
    This view handles user registration with username, email, and password.
    """
    def has_permission(self, request, view):
        """
        Check if the request has permission to access this view.
        
        Only allows POST requests (user creation).
        
        Args:
            request: HTTP request
            view: Current view
            
        Returns:
            bool: True if the request method is POST
        """
        return request.method == "POST"

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a new user.
        
        Validates the request data and creates a new user with username, email, and password.
        
        Args:
            request: HTTP request with user data
            
        Returns:
            Response: New user data with 201 Created status
            
        Raises:
            ValidationError: If the provided data is invalid
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = User.objects.create_user_username_email_password(
            username=username, email=email, password=password
        )
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
