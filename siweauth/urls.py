from django.urls import path
from .views import TokenObtainPairView, SIWETokenObtainPairView, get_nonce, who_am_i

urlpatterns = [
    path('api/siwetoken/', SIWETokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/get_nonce/', get_nonce.as_view(), name='get_nonce'),
    path('api/who_am_i/', who_am_i, name='who_am_i'),
]