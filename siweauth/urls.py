from django.urls import path
from .views import TokenObtainPairView, SIWETokenObtainPairView, CreateUserView, get_nonce, who_am_i
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('siwetoken/', SIWETokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('get_nonce/', get_nonce, name='get_nonce'),
    path('who_am_i/', who_am_i, name='who_am_i'),
    path('register/', CreateUserView.as_view(), name='register'),
]