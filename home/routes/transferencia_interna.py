from django.urls import path

from home.views.transferencia_interna import (
    transferencia_interna,
    dados_aluno_transferencia,
    salvar_transferencia_interna,
)

app_name = "transferencia_interna"

urlpatterns = [
    path(
        "",
        transferencia_interna,
        name="inicio",
    ),
    path(
        "aluno/<int:aluno_id>/",
        dados_aluno_transferencia,
        name="dados_aluno",
    ),
    path(
        "salvar/",
        salvar_transferencia_interna,
        name="salvar",
    ),
]
