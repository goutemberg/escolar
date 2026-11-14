from django.urls import path

from home.views.dashboard_diretor import (
    dashboard_diretor,
    dashboard_diretor_turma,
    dashboard_diretor_aluno,
)

urlpatterns = [
    # ==========================================================
    # DASHBOARD PRINCIPAL
    # ==========================================================
    path(
        "",
        dashboard_diretor,
        name="dashboard_diretor",
    ),
    # ==========================================================
    # DIAGNÓSTICO DA TURMA
    # ==========================================================
    path(
        "turma/<int:turma_id>/",
        dashboard_diretor_turma,
        name="dashboard_diretor_turma",
    ),
    # ==========================================================
    # DIAGNÓSTICO DO ALUNO
    # ==========================================================
    path(
        "aluno/<int:aluno_id>/",
        dashboard_diretor_aluno,
        name="dashboard_diretor_aluno",
    ),
]
