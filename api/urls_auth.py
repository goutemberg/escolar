from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from api.views.auth import CPFTokenObtainPairView, teste_api

urlpatterns = [
    path("teste/", teste_api, name="teste_api"),
    path("token/", CPFTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/logout/", TokenBlacklistView.as_view(), name="token_blacklist"),
]