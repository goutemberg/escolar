from django.urls import path
from home.views.relatorio_individual import (
    relatorio_individual_view,
    salvar_relatorio_individual,
    buscar_relatorio_individual,
)

app_name = "relatorio_individual"

urlpatterns = [
    path(
        "relatorio-individual/",
        relatorio_individual_view,
        name="relatorio_individual",
    ),
    path(
        "relatorio-individual/salvar/",
        salvar_relatorio_individual,
        name="salvar_relatorio_individual",
    ),
    path(
        "api/relatorio-individual/",
        buscar_relatorio_individual,
        name="buscar_relatorio_individual",
    ),
]