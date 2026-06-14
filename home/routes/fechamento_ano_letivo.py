from django.urls import path
from home.views.fechamento_ano_letivo import (
    tela_fechamento_ano,
    fechar_ano_letivo
)

app_name = "fechar_ano_letivo"

urlpatterns = [
   path("fechamento/", tela_fechamento_ano, name="tela_fechamento_ano"),
   path("fechamento/fechar/", fechar_ano_letivo, name="fechar_ano_letivo"),
]