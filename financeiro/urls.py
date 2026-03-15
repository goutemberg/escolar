from django.urls import path
from financeiro.views.views_mensalidades import (
    listar_mensalidades,
    gerar_mensalidades,
    dar_baixa_mensalidade
)

urlpatterns = [

    path(
        "mensalidades/",
        listar_mensalidades,
        name="listar_mensalidades"
    ),

    path(
        "mensalidades/gerar/",
        gerar_mensalidades,
        name="gerar_mensalidades"
    ),

    path(
        "mensalidades/<int:mensalidade_id>/baixar/",
        dar_baixa_mensalidade,
        name="dar_baixa_mensalidade"
    ),

]