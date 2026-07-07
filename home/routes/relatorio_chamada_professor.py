from django.urls import path

from home.views.relatorio_chamada_professor import (
    relatorio_chamada_professor,
    relatorio_chamada_professor_pdf,
)

app_name = "relatorio_chamada_professor"

urlpatterns = [
    path(
        "relatorio-chamada-professor/",
        relatorio_chamada_professor,
        name="relatorio_chamada_professor",
    ),
    path(
        "relatorio-chamada-professor/pdf/",
        relatorio_chamada_professor_pdf,
        name="relatorio_chamada_professor_pdf",
    ),
]
