"""
Perfis (Roles) oficiais do sistema.

Este módulo centraliza todos os papéis utilizados pelo RBAC.
Os nomes definidos aqui são utilizados para criar os Groups
do Django e nunca devem ser escritos diretamente em outras
partes da aplicação.
"""


class Roles:
    """Papéis oficiais do sistema."""

    ADMINISTRADOR = "Administrador"
    DIRETOR = "Diretor"
    COORDENADOR = "Coordenador"
    PROFESSOR = "Professor"
    SECRETARIA = "Secretaria"
    FINANCEIRO = "Financeiro"
    RESPONSAVEL = "Responsável"

    @classmethod
    def all(cls):
        """
        Retorna todos os papéis oficiais do sistema.
        """
        return [
            cls.ADMINISTRADOR,
            cls.DIRETOR,
            cls.COORDENADOR,
            cls.PROFESSOR,
            cls.SECRETARIA,
            cls.FINANCEIRO,
            cls.RESPONSAVEL,
        ]
