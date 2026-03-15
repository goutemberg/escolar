from django.urls import path
from home.views_root import salvar_turma
from home.views.turmas import (

    listar_turmas,
    detalhe_turma,

    pagina_nome_turma,
    cadastrar_nome_turma,
    listar_nomes_turma,
    editar_nome_turma,
    excluir_nome_turma,

    cadastro_turma,
    remover_aluno_turma,
    remover_professor_turma,

    api_detalhe_turma,

    duplicar_turma,
    inativar_turma,
    excluir_turma,
)

app_name = "turmas"

urlpatterns = [

    # ============================
    # LISTAGEM E DETALHE
    # ============================

    path("listar/", listar_turmas, name="listar"),

    path("<int:turma_id>/", detalhe_turma, name="detalhe"),


    # ============================
    # CREATE / EDIT
    # ============================

    path("cadastrar/", cadastro_turma, name="cadastrar"),

    path("<int:turma_id>/editar/", cadastro_turma, name="editar"),


    # ============================
    # AÇÕES DA TURMA
    # ============================

    path("<int:turma_id>/duplicar/", duplicar_turma, name="duplicar"),

    path("<int:turma_id>/inativar/", inativar_turma, name="inativar"),

    path("<int:turma_id>/excluir/", excluir_turma, name="excluir"),

    path("salvar/", salvar_turma, name="salvar_turma"),


    # ============================
    # AÇÕES RÁPIDAS
    # ============================

    path(
        "<int:turma_id>/remover-aluno/",
        remover_aluno_turma,
        name="remover_aluno",
    ),

    path(
        "<int:turma_id>/remover-professor/",
        remover_professor_turma,
        name="remover_professor",
    ),


    # ============================
    # API
    # ============================

    path(
        "api/turmas/<int:turma_id>/",
        api_detalhe_turma,
        name="api_detalhe_turma",
    ),


    # ============================
    # NOMES DE TURMA
    # ============================

    path("nome/", pagina_nome_turma, name="pagina_nome"),

    path("nome/cadastrar/", cadastrar_nome_turma, name="cadastrar_nome"),

    path("nome/listar/", listar_nomes_turma, name="listar_nomes"),

    path("nome/editar/", editar_nome_turma, name="editar_nome"),

    path("nome/excluir/", excluir_nome_turma, name="excluir_nome"),
]