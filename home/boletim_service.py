import json

from home.models import Boletim
from home.utils import montar_boletim


def gerar_e_salvar_boletim(aluno, turma):

    dados = montar_boletim(aluno, turma)

    boletim_obj, _ = Boletim.objects.update_or_create(
        aluno=aluno,
        turma=turma,
        defaults={
            "dados": dados
        }
    )

    return boletim_obj