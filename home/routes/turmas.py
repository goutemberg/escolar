from django.urls import path
from home.views.turmas import (
    listar_turmas,
    detalhe_turma,
    pagina_nome_turma,
    cadastrar_nome_turma,
    listar_nomes_turma,
    editar_nome_turma,
    excluir_nome_turma,
    cadastro_turma

)

app_name = "turmas"

urlpatterns = [

    # ============================
    # LISTAGEM E DETALHE DE TURMA
    # ============================
    path("listar/", listar_turmas, name="listar"),
    path("<int:turma_id>/", detalhe_turma, name="detalhe"),

    # ============================
    # NOMES DE TURMA
    # ============================
    path("nome/", pagina_nome_turma, name="pagina_nome"),
    path("nome/cadastrar/", cadastrar_nome_turma, name="cadastrar_nome"),
    path("nome/listar/", listar_nomes_turma, name="listar_nomes"),
    path("nome/editar/", editar_nome_turma, name="editar_nome"),
    path("nome/excluir/", excluir_nome_turma, name="excluir_nome"),
    path("cadastrar/", cadastro_turma, name="cadastrar_turma"),
]

