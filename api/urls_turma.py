from django.urls import path
from .views.turma import alunos_da_turma, minhas_turmas 

urlpatterns = [

    path('minhas-turmas/', minhas_turmas, name='minhas_turmas'),
    path('turmas/<int:turma_id>/alunos/', alunos_da_turma, name='alunos_da_turma'),
   
]