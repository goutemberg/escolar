from django.urls import path
from home.views.api_alunos_por_turma import alunos_por_turma

app_name = "api_alunos"

urlpatterns = [
    path(
        "api/alunos-por-turma/",
        alunos_por_turma,
        name="alunos_por_turma",
    ),
]
