from django.urls import path
from home.views.avaliacao import (
    avaliacoes,
    excluir_avaliacao,
    tipos_avaliacao,
    lancar_notas,
    editar_avaliacao,
)

app_name = "avaliacoes"

urlpatterns = [

    path("tipos-avaliacao/", tipos_avaliacao, name="tipos_avaliacao"),

    path("", avaliacoes, name="avaliacoes"),

    path("excluir/<int:avaliacao_id>/", excluir_avaliacao, name="excluir_avaliacao"),

    path("lancar-notas/", lancar_notas, name="lancar_notas"),

    path("editar/<int:avaliacao_id>/", editar_avaliacao, name="editar_avaliacao"),

]
