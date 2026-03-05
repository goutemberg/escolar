from django.urls import path
from home.views.registro_pedagogico import (
    registro_pedagogico_view,
    buscar_disciplinas_por_turma,
    salvar_registro_pedagogico,
    buscar_registro_pedagogico,
)

app_name = "registro_pedagogico"

urlpatterns = [
    path(
        "registro-pedagogico/",
        registro_pedagogico_view,
        name="registro_pedagogico",
    ),
    path(
        "api/disciplinas-por-turma/",
        buscar_disciplinas_por_turma,
        name="buscar_disciplinas_por_turma",
    ),
    path(
        "registro-pedagogico/salvar/",
        salvar_registro_pedagogico,
        name="salvar_registro_pedagogico",
    ),
    path(
        "api/registro-pedagogico/",
        buscar_registro_pedagogico,
        name="buscar_registro_pedagogico",
    ),
]