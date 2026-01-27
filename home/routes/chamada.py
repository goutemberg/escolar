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
    disciplinas_por_turma
)

app_name = "chamada"

urlpatterns = [
    # Telas
    path("registrar/", tela_chamada, name="registrar_chamada"),
    path("historico/", listar_chamadas, name="listar_chamadas"),
    path("historico/<int:chamada_id>/", detalhe_chamada, name="detalhe_chamada"),

    # Ações
    path("registrar/salvar/", salvar_presencas, name="salvar_presencas"),
    path("pdf/<int:chamada_id>/", pdf_chamada, name="pdf_chamada"),
    path("editar/<int:chamada_id>/", editar_chamada, name="editar_chamada"),
    path("editar/<int:chamada_id>/salvar/", atualizar_chamada, name="atualizar_chamada"),

    path("api/carregar_alunos/<int:turma_id>/", api_carregar_alunos, name="api_carregar_alunos"),
    path("api/disciplinas_por_turma/<int:turma_id>/", disciplinas_por_turma, name="disciplinas_por_turma")

]
