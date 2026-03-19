from django.urls import path
from financeiro.views.gerar_recibo import(
    gerar_recibo
)
from financeiro.views.views_mensalidades import (
    listar_mensalidades,
    gerar_mensalidades,
    dar_baixa_mensalidade,
    exportar_csv,
    exportar_excel,
    estornar_mensalidade,
    atualizar_desconto,
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

    path('financeiro/recibo/<int:mensalidade_id>/', gerar_recibo, name='gerar_recibo'),

       path('mensalidades/exportar/csv/',
         exportar_csv,
         name='exportar_csv'),

    path('mensalidades/exportar/excel/',
         exportar_excel,
         name='exportar_excel'),

    path('mensalidades/<int:id>/estornar/', estornar_mensalidade),
    path("mensalidades/<int:id>/desconto/", atualizar_desconto, name="atualizar_desconto")

]