from django.urls import path

from home.views.chamada_aluno import (
    tela_chamada,
    api_carregar_alunos,
    salvar_presencas,
    listar_chamadas,
    detalhe_chamada,
    pdf_chamada,
    editar_chamada,
    atualizar_chamada,
    disciplinas_por_turma,
    api_disciplinas_por_turma,
    api_datas_chamada,
    relatorio_chamadas_pdf,
    export_resumo_mensal_csv,
    export_resumo_mensal_excel,
    resumo_mensal_turma_professor,
    relatorio_anual_chamadas,
    relatorio_anual_chamadas_pdf,
    relatorio_anual_chamadas_excel,
    excluir_chamada,
)

app_name = "chamada"

urlpatterns = [
    # =====================================================
    # TELAS
    # =====================================================
    path("registrar/", tela_chamada, name="registrar_chamada"),
    path("historico/", listar_chamadas, name="listar_chamadas"),
    path(
        "historico/<int:chamada_id>/",
        detalhe_chamada,
        name="detalhe_chamada",
    ),
    # =====================================================
    # AÇÕES
    # =====================================================
    path(
        "registrar/salvar/",
        salvar_presencas,
        name="salvar_presencas",
    ),
    path(
        "pdf/<int:chamada_id>/",
        pdf_chamada,
        name="pdf_chamada",
    ),
    path(
        "editar/<int:chamada_id>/",
        editar_chamada,
        name="editar_chamada",
    ),
    path(
        "editar/<int:chamada_id>/salvar/",
        atualizar_chamada,
        name="atualizar_chamada",
    ),
    path(
        "excluir/<int:chamada_id>/",
        excluir_chamada,
        name="excluir_chamada",
    ),
    # =====================================================
    # APIs
    # =====================================================
    path(
        "api/carregar-alunos/<int:turma_id>/",
        api_carregar_alunos,
        name="api_carregar_alunos",
    ),
    # Mantida para o registro de chamada
    path(
        "api/disciplinas-por-turma/<int:turma_id>/",
        disciplinas_por_turma,
        name="disciplinas_por_turma",
    ),
    # Nova API utilizada pelo Histórico
    path(
        "api/disciplinas/",
        api_disciplinas_por_turma,
        name="api_disciplinas_por_turma",
    ),
    path(
        "api/datas-chamada/",
        api_datas_chamada,
        name="api_datas_chamada",
    ),
    # =====================================================
    # RELATÓRIOS
    # =====================================================
    path(
        "relatorios/resumo-mensal/",
        resumo_mensal_turma_professor,
        name="relatorio_resumo_mensal",
    ),
    path(
        "relatorios/chamadas/pdf/",
        relatorio_chamadas_pdf,
        name="relatorio_chamadas_pdf",
    ),
    path(
        "relatorios/chamadas/anual/",
        relatorio_anual_chamadas,
        name="relatorio_anual_chamadas",
    ),
    path(
        "relatorios/anual/pdf/",
        relatorio_anual_chamadas_pdf,
        name="relatorio_anual_chamadas_pdf",
    ),
    path(
        "relatorios/anual/excel/",
        relatorio_anual_chamadas_excel,
        name="relatorio_anual_chamadas_excel",
    ),
    # =====================================================
    # EXPORTAÇÕES
    # =====================================================
    path(
        "relatorios/resumo-mensal/csv/",
        export_resumo_mensal_csv,
        name="export_resumo_mensal_csv",
    ),
    path(
        "relatorios/resumo-mensal/excel/",
        export_resumo_mensal_excel,
        name="export_resumo_mensal_excel",
    ),
]
