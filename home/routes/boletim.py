from django.urls import path
from home.views.boletim import (
    gerar_pdf_boletim,
    boletim_turma
)

app_name = "boletim"

urlpatterns = [

    path("boletim/pdf/<int:aluno_id>/", gerar_pdf_boletim, name="boletim_pdf"),
    path("boletim/turma/<int:turma_id>/", boletim_turma, name="boletim_turma"),



]
