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
    relatorio_chamadas_pdf,
    export_resumo_mensal_csv,
    export_resumo_mensal_excel,
    resumo_mensal_turma_professor,
    relatorio_anual_chamadas,
    relatorio_anual_chamadas_pdf,
    relatorio_anual_chamadas_excel,
)

app_name = "chamada"

urlpatterns = [
    # Telas
    path("registrar/", tela_chamada, name="registrar_chamada"),
    path("historico/", listar_chamadas, name="listar_chamadas"),
    path("historico/<int:chamada_id>/", detalhe_chamada, name="detalhe_chamada"),

    # Relatórios
    path("relatorios/resumo-mensal/", resumo_mensal_turma_professor, name="relatorio_resumo_mensal"),
    path("relatorios/chamadas/pdf/", relatorio_chamadas_pdf, name="relatorio_chamadas_pdf"),
    path("relatorios/chamadas/anual/", relatorio_anual_chamadas, name="relatorio_anual_chamadas"),
    path("relatorios/anual/excel/",relatorio_anual_chamadas_excel, name="relatorio_anual_chamadas_excel"),


    # Ações
    path("registrar/salvar/", salvar_presencas, name="salvar_presencas"),
    path("pdf/<int:chamada_id>/", pdf_chamada, name="pdf_chamada"),
    path("editar/<int:chamada_id>/", editar_chamada, name="editar_chamada"),
    path("editar/<int:chamada_id>/salvar/", atualizar_chamada, name="atualizar_chamada"),

    # APIs
    path("api/carregar_alunos/<int:turma_id>/", api_carregar_alunos, name="api_carregar_alunos"),
    path("api/disciplinas_por_turma/<int:turma_id>/", disciplinas_por_turma, name="disciplinas_por_turma"),

    # Exportações
    path("relatorios/resumo-mensal/csv/", export_resumo_mensal_csv, name="export_resumo_mensal_csv"),
    path("relatorios/resumo-mensal/excel/", export_resumo_mensal_excel, name="export_resumo_mensal_excel"),
    path("relatorios/anual/pdf/", relatorio_anual_chamadas_pdf, name="relatorio_anual_chamadas_pdf"
),
]

