from django.template.loader import get_template
from datetime import datetime
from django.utils import timezone
import re


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


def validar_senha_forte(senha):
    if len(senha) < 8:
        return "A senha deve ter pelo menos 8 caracteres"

    if not re.search(r"[A-Z]", senha):
        return "A senha deve conter letra maiúscula"

    if not re.search(r"[a-z]", senha):
        return "A senha deve conter letra minúscula"

    if not re.search(r"\d", senha):
        return "A senha deve conter número"

    return None


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]

    return request.META.get('REMOTE_ADDR')



def get_escola_ativa(request):
    from home.models import Escola
    escola_id = request.session.get("escola_id")

    if escola_id:
        try:
            return Escola.objects.get(id=escola_id)
        except Escola.DoesNotExist:
            return None

    return None


def arredondar_media_personalizada(media):
    if media is None:
        return None

    media = float(media)

    # 🔥 REGRA ESPECIAL SÓ PARA 7.x
    if 7.0 <= media < 8.0:
        if media <= 7.2:
            return 7.0
        elif media <= 7.7:
            return 7.5
        else:
            return 8.0

    return round(media)


def get_ano_ativo():
    from .models import AnoLetivo  

    return AnoLetivo.objects.filter(
        ativo=True,
        encerrado=False
    ).first()


def get_turmas_ativas(escola, incluir_sem_ano=False):
    from .models import Turma
    from .utils import get_ano_ativo

    ano = get_ano_ativo()

    if not ano:
        return Turma.objects.none()

    qs = Turma.objects.filter(
        escola=escola,
        ano_letivo=ano
    )

    if incluir_sem_ano:
        qs = qs | Turma.objects.filter(
            escola=escola,
            ano_letivo__isnull=True
        )

    return qs
