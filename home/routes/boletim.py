from django.urls import path
from home.views.boletim import (
    gerar_pdf_boletim,
    boletim_turma,
)

app_name = "boletim"

urlpatterns = [


path("turma/<int:turma_id>/", boletim_turma, name="boletim_turma"),

]
