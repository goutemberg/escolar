from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CPFTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "cpf"

    def validate(self, attrs):
        cpf = attrs.get("cpf")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=cpf,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError("CPF ou senha inválidos.")

        if not user.is_active:
            raise serializers.ValidationError("Usuário inativo.")

        refresh = self.get_token(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "usuario": {
                "id": user.id,
                "nome": getattr(user, "first_name", "") or getattr(user, "username", ""),
                "cpf": getattr(user, "cpf", "") or getattr(user, "username", ""),
                "role": getattr(user, "role", ""),
                "escola_id": getattr(user, "escola_id", None),
            }
        }