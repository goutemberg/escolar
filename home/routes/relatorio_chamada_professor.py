from django.urls import path

from home.views.relatorio_chamada_professor import relatorio_chamada_professor

app_name = "relatorio_chamada_professor"

urlpatterns = [
    path(
        "relatorio-chamada-professor/",
        relatorio_chamada_professor,
        name="relatorio_chamada_professor",
    ),
]
