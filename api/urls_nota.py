from django.urls import path
from .views.nota import (
    listar_avaliacoes_api,
    consultar_notas_api,
    salvar_notas_api,
)

urlpatterns = [
    path("notas/avaliacoes/", listar_avaliacoes_api, name="listar_avaliacoes_api"),
    path("notas/consultar/", consultar_notas_api, name="consultar_notas_api"),
    path("notas/salvar/", salvar_notas_api, name="salvar_notas_api"),
]