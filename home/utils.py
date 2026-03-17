from django.template.loader import get_template
from datetime import datetime
from django.utils import timezone




def gerar_matricula_unica():
    from .models import Aluno
    prefixo = "ALU"
    ano = datetime.now().year
    base = f"{prefixo}{ano}"

    ultimo_aluno = (
        Aluno.objects.filter(matricula__startswith=base)
        .order_by('-id')
        .first()
    )
    numero = 1

    if ultimo_aluno:
        try:
            numero = int(ultimo_aluno.matricula[-4:]) + 1
        except:
            pass

    nova_matricula = f"{base}{str(numero).zfill(4)}"
    return nova_matricula


def gerar_avaliacoes_para_turma(turma):
    from .models import Avaliacao, Disciplina, ModeloAvaliacao
    escola = turma.escola

    bimestres = [1, 2, 3, 4]

    disciplinas = Disciplina.objects.filter(
        turmadisciplina__turma=turma
    )

    modelos = ModeloAvaliacao.objects.filter(
        escola=escola,
        ativo=True
    )

    for disciplina in disciplinas:

        for bimestre in bimestres:

            for modelo in modelos:

                Avaliacao.objects.get_or_create(
                    turma=turma,
                    disciplina=disciplina,
                    bimestre=bimestre,
                    descricao=modelo.nome,
                    escola=escola,
                    defaults={
                        "tipo": modelo.tipo,
                        "data": timezone.now().date()
                    }
                )
