from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.views import TokenObtainPairView

from api.serializers.auth import CPFTokenObtainPairSerializer


def teste_api(request):
    return JsonResponse({
        "status": "ok",
        "mensagem": "API da escolinha funcionando"
    })


class CPFTokenObtainPairView(TokenObtainPairView):
    serializer_class = CPFTokenObtainPairSerializer