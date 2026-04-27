from django.urls import path
from home.views.boletim import (
    gerar_pdf_boletim,
    boletim_turma,
)

app_name = "boletim"

urlpatterns = [


path("turma/<int:turma_id>/", boletim_turma, name="boletim_turma"),
path("boletim-pdf/<int:aluno_id>/<int:turma_id>/", gerar_pdf_boletim, name="gerar_pdf_boletim"),

]
