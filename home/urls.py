from django.urls import path, include
from . import views_root

urlpatterns = [

    # --------------------------------
    # Dashboard / Index
    # --------------------------------
    path('', views_root.index, name='index'),

    # --------------------------------
    # Escola
    # --------------------------------
    path('minha_escola/', views_root.visualizar_escola, name='minha_escola'),
    path('editar_escola/', views_root.editar_escola, name='editar_escola'),

    # --------------------------------
    # Professor
    # --------------------------------
    path('cadastro_professor/', views_root.cadastro_professor, name='cadastro_professor'),
    path('cadastrar_professor_banco/', views_root.cadastrar_professor_banco, name='cadastrar_professor_banco'),
    path('listar_professores/', views_root.listar_professores, name='listar_professores'),
    path('editar_professor/<int:prof_id>/', views_root.editar_professor, name='editar_professor'),
    path('alternar_status_professor/<int:prof_id>/', views_root.alternar_status_professor, name='alternar_status_professor'),
    path("professores/<int:id>/toggle-status/", views_root.toggle_status_professor, name="toggle_status_professor"),
    path('professores/<int:professor_id>/editar/', views_root.form_professor, name='editar_professor'),
    path('api/professores/<int:professor_id>/', views_root.api_professor_detalhe),


    # --------------------------------
    # Aluno
    # --------------------------------
    path('cadastro_aluno/', views_root.cadastrar_aluno, name='cadastro_aluno'),
    path('salvar_aluno/', views_root.salvar_aluno, name='salvar_aluno'),
    path('alternar_status_aluno/<int:aluno_id>/', views_root.alternar_status_aluno, name='alternar_status_aluno'),
    path('listar_aluno/', views_root.listar_alunos, name='listar_aluno'),
    path('alunos/<int:aluno_id>/editar/', views_root.editar_aluno_view, name='editar_aluno',
),
    


    # PDFs do aluno
    path("alunos/<int:pk>/pdf/", views_root.aluno_requerimento_pdf, name="aluno_requerimento"),
    path('aluno/reimprimir/', views_root.reimprimir_documentos_aluno, name='reimprimir_documentos_aluno'),
    path("alunos/<int:pk>/comprovante/", views_root.comprovante_matricula_pdf, name="comprovante_matricula_pdf"),
    path("aluno/ficha/<int:pk>/", views_root.ficha_cadastral_pdf, name="ficha_cadastral_pdf"),

    # --------------------------------
    # Funcionário
    # --------------------------------
    path('cadastro_funcionarios/', views_root.cadastro_funcionarios, name='cadastro_funcionarios'),
    path('cadastrar-funcionario/', views_root.cadastrar_funcionario_banco, name='cadastrar_funcionario_banco'),

    # --------------------------------
    # Buscar Pessoa
    # --------------------------------
    path('buscar_pessoa/', views_root.buscar_pessoa, name='buscar_pessoa'),
    path('autocomplete_pessoa/', views_root.autocomplete_pessoa, name='autocomplete_pessoa'),

    # --------------------------------
    # Impressão / Relatórios
    # --------------------------------
    path('imprimir_relatorios/', views_root.impressao_dados, name='imprimir_relatorios'),

    # --------------------------------
    # Notas / Boletim
    # --------------------------------
    path('registrar_notas/', views_root.registrar_notas, name='registrar_notas'),
    path('lancar_notas/', views_root.lancar_notas, name='lancar_notas'),

    path('boletins/', views_root.listar_turmas_para_boletim, name='listar_turmas_boletim'),
    path('boletins/<int:aluno_id>/', views_root.visualizar_boletim, name='visualizar_boletim'),

    # --------------------------------
    # Disciplinas
    # --------------------------------
    path('disciplinas/cadastrar/', views_root.cadastrar_disciplina, name='cadastrar_disciplina'),
    path('disciplinas/', views_root.pagina_cadastrar_disciplina, name='pagina_cadastrar_disciplina'),
    path('disciplinas/listar/', views_root.listar_disciplinas, name='listar_disciplinas'),
    path('disciplinas/editar/', views_root.editar_disciplina, name='editar_disciplina'),
    path('disciplinas/excluir/', views_root.excluir_disciplina, name='excluir_disciplina'),

    # --------------------------------
    # Usuário sem escola
    # --------------------------------
    path('erro/sem-escola/', views_root.usuario_sem_escola, name='usuario_sem_escola'),

    # --------------------------------
    # Chamada / Diário de Classe
    # --------------------------------
    path('diario-classe/', views_root.diario_classe, name='diario_classe'),
    path('salvar-chamada/', views_root.salvar_chamada, name='salvar_chamada'),
    path('buscar-alunos/<int:turma_id>/', views_root.buscar_alunos, name='buscar_alunos'),
    path('diario-classe/visualizar/', views_root.visualizar_chamada, name='visualizar_chamada'),
    path('diario-classe/editar-registro/<int:registro_id>/', views_root.editar_registro, name='editar_registro'),

    # --------------------------------
    # Login / Logout
    # --------------------------------
    path('login/', views_root.login_view, name='login'),
    path('logout/', views_root.logout_view, name='logout'),

    # --------------------------------
    # Troca de senha / Primeiro acesso
    # --------------------------------
    path('trocar_senha/', views_root.verificar_senha_temporaria, name='trocar_senha'),
    path('trocar_senha_api/', views_root.trocar_senha_api, name='trocar_senha_api'),

    # --------------------------------
    # Importar dados
    # --------------------------------
    path('importar_alunos/', views_root.importar_alunos, name='importar_alunos'),

    # --------------------------------
    # Admin temporário
    # --------------------------------
    path("criar-admin-temp/", views_root.create_admin_temp, name='criar-admin-temp'),

    path("chamada/", include(("home.routes.chamada", "chamada"), namespace="chamada")),
    path("turmas/", include(("home.routes.turmas", "turmas"), namespace="turmas")),
    path("", include(("home.routes.matricula_em_lote", "matricula_lote"), namespace="matricula_lote")),
    path("", include(("home.routes.registro_pedagogico", "registro_pedagogico"), namespace="registro_pedagogico")),
    path("", include(("home.routes.api_alunos_por_turma", "api_alunos_por_turma"), namespace="api_alunos_por_turma")),

]
