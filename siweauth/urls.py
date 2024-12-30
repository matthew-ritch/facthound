from django.urls import path
from .views import TokenObtainPairView, get_nonce

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/get_nonce/', get_nonce.as_view(), name='get_nonce'),
]