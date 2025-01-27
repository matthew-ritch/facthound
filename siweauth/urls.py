from django.urls import path
from .views import TokenObtainPairView, SIWETokenObtainPairView, CreateUserView, get_nonce, who_am_i
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('api/siwetoken/', SIWETokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/get_nonce/', get_nonce, name='get_nonce'),
    path('api/who_am_i/', who_am_i, name='who_am_i'),
    path('api/register/', CreateUserView.as_view(), name='register'),
]