from django.urls import path
from home.views.matricula_em_lote import preview_matricula
from home.views.matricula_em_lote import (
    salvar_matricula_lote,
    registro_matricula_lote
)

app_name = "matricula_lote"

urlpatterns = [
    path(
        "alunos/registro-lote/",
        registro_matricula_lote,
        name="registro_matricula_lote"
    ),
    path(
        "alunos/salvar-lote/",
        salvar_matricula_lote,
        name="salvar_matricula_lote"
    ),

    path('preview-matricula/', preview_matricula, name='preview_matricula'),
]
