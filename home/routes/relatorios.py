from django.urls import path
from home.views.relatorios import (
   presenca_aluno_mensal,
   export_presenca_aluno_mensal_excel,
   pdf_presenca_aluno_mensal,
   pdf_presenca_aluno_individual

)

app_name = "relatorios"

urlpatterns = [

    path("presenca/aluno/", presenca_aluno_mensal, name="presenca_aluno_mensal"),
    path("relatorios/presenca-aluno-mensal/excel/", export_presenca_aluno_mensal_excel, name="export_presenca_aluno_mensal_excel"),
    path("relatorios/presenca-aluno-mensal/pdf/", pdf_presenca_aluno_mensal, name="pdf_presenca_aluno_mensal"),
    path("relatorios/presenca-aluno/pdf/<int:aluno_id>/", pdf_presenca_aluno_individual, name="pdf_presenca_aluno_individual"),


    
]
