from django.urls import path

from home.views.matricula import (
    listar_matriculas,
    nova_matricula,
    salvar_matricula,
    visualizar_matricula,
    editar_matricula,
    salvar_edicao_matricula,
    declaracao_matrícula,
)

app_name = "matricula"


urlpatterns = [
    path(
        "",
        listar_matriculas,
        name="listar",
    ),
    path(
        "nova/",
        nova_matricula,
        name="nova",
    ),
    path(
        "salvar/",
        salvar_matricula,
        name="salvar",
    ),
    path(
        "<int:matricula_id>/visualizar/",
        visualizar_matricula,
        name="visualizar",
    ),
    path(
        "<int:matricula_id>/editar/",
        editar_matricula,
        name="editar",
    ),
    path(
        "<int:matricula_id>/editar/salvar/",
        salvar_edicao_matricula,
        name="salvar_edicao",
    ),
    path(
        "<int:matricula_id>/declaracao/",
        declaracao_matrícula,
        name="declaracao",
    ),
]
