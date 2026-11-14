from django.urls import path

from home.views.fechamento_ano_letivo import (
    fechamento_ano_letivo,
    fechar_ano_letivo,
    abrir_ano_letivo,
)

urlpatterns = [
    path("", fechamento_ano_letivo, name="inicio"),
    path(
        "fechar/",
        fechar_ano_letivo,
        name="fechar_ano_letivo",
    ),
    path(
        "abrir/",
        abrir_ano_letivo,
        name="abrir_ano_letivo",
    ),
]
