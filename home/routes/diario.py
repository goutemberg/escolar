from django.urls import path
from home.views.diario import (
    
    api_disciplinas_por_turma,
    api_listar_diario,
    salvar_diario_classe,
    diario_classe_pdf
)

app_name = "diario_classe"

urlpatterns = [
    

    
    path("api/disciplinas_por_turma/<int:turma_id>/", api_disciplinas_por_turma, name="disciplinas_por_turma"),
    path("listar/", api_listar_diario, name="listar_diario"),
    path("salvar/", salvar_diario_classe, name="salvar_diario_classe"),
    path("pdf/", diario_classe_pdf, name="pdf_diario_classe"),


]