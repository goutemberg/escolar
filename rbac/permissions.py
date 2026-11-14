"""
Permissões oficiais do sistema.

Todas as permissões utilizadas pela aplicação devem ser
declaradas neste arquivo.

As permissões seguem o padrão do Django:

<app_label>.<action>_<model>

Exemplo:
escolinha.view_aluno
escolinha.add_aluno
escolinha.change_aluno
escolinha.delete_aluno
"""


class Permissions:

    class Alunos:
        VIEW = "escolinha.view_aluno"
        ADD = "escolinha.add_aluno"
        EDIT = "escolinha.change_aluno"
        DELETE = "escolinha.delete_aluno"

    class Turmas:
        VIEW = "escolinha.view_turma"
        ADD = "escolinha.add_turma"
        EDIT = "escolinha.change_turma"
        DELETE = "escolinha.delete_turma"

    class Disciplinas:
        VIEW = "escolinha.view_disciplina"
        ADD = "escolinha.add_disciplina"
        EDIT = "escolinha.change_disciplina"
        DELETE = "escolinha.delete_disciplina"

    class Chamada:
        VIEW = "escolinha.view_chamada"
        ADD = "escolinha.add_chamada"
        EDIT = "escolinha.change_chamada"
        DELETE = "escolinha.delete_chamada"

    class Notas:
        VIEW = "escolinha.view_nota"
        ADD = "escolinha.add_nota"
        EDIT = "escolinha.change_nota"
        DELETE = "escolinha.delete_nota"
