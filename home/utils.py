from django.template.loader import get_template
from datetime import datetime
from django.utils import timezone
import re

from collections import defaultdict

from home.models import (
    Nota,
    Disciplina,
    Avaliacao,
    Chamada,
    Presenca,
)


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


def montar_boletim(aluno, turma):

    escola = turma.escola

    # ================================
    # DISCIPLINAS
    # ================================
    disciplinas = Disciplina.objects.filter(
        turmadisciplina__turma=turma,
        escola=escola
    ).distinct()

    # ================================
    # AVALIAÇÕES
    # ================================
    avaliacoes = Avaliacao.objects.filter(
        turma=turma,
        escola=escola
    ).select_related("disciplina", "tipo")

    # ================================
    # NOTAS DO ALUNO
    # ================================
    notas = Nota.objects.filter(
        aluno=aluno,
        avaliacao__in=avaliacoes
    ).select_related("avaliacao")

    # ================================
    # ORGANIZAÇÃO DAS NOTAS
    # ================================
    notas_por_disciplina = defaultdict(lambda: defaultdict(list))

    for nota in notas:

        disciplina_id = nota.avaliacao.disciplina_id
        bimestre = nota.avaliacao.bimestre

        # 🔥 PRIORIDADE CORRETA
        if nota.recuperacao is not None:
            valor = float(nota.recuperacao)

        elif nota.valor is not None:
            valor = float(nota.valor)

        elif nota.conceito:
            valor = nota.conceito

        else:
            continue

        notas_por_disciplina[disciplina_id][bimestre].append({
            "valor": valor,
            "tipo": nota.avaliacao.tipo.nome if nota.avaliacao.tipo else "Avaliação"
        })

    # ================================
    # FALTAS
    # ================================
    faltas_por_disciplina = defaultdict(int)

    chamadas = Chamada.objects.filter(
        diario__turma=turma
    ).select_related("diario__disciplina")

    presencas = Presenca.objects.filter(
        aluno=aluno,
        chamada__in=chamadas
    ).select_related("chamada__diario")

    for p in presencas:
        if not p.presente:
            disciplina_id = p.chamada.diario.disciplina_id
            faltas_por_disciplina[disciplina_id] += 1

    # ================================
    # MONTAGEM DO BOLETIM
    # ================================
    boletim = []

    for disciplina in disciplinas:

        bimestres = {}
        notas_detalhadas = {}

        for b in [1, 2, 3, 4]:

            lista = notas_por_disciplina[disciplina.id][b]
            notas_detalhadas[b] = lista

            # 🔥 SÓ NUMÉRICO ENTRA NA MÉDIA
            valores = [
                n["valor"]
                for n in lista
                if isinstance(n["valor"], (int, float))
            ]

            if valores:
                media = sum(valores) / len(valores)
                bimestres[b] = arredondar_media_personalizada(media)
            else:
                bimestres[b] = None

        # ================================
        # MÉDIA FINAL
        # ================================
        medias_validas = [
            v for v in bimestres.values()
            if v is not None
        ]

        media_final = None

        if medias_validas:
            media_final = sum(medias_validas) / len(medias_validas)
            media_final = arredondar_media_personalizada(media_final)

        # ================================
        # STATUS
        # ================================
        if media_final is None:
            status = "-"

        elif media_final >= 7:
            status = "Aprovado"

        elif media_final >= 5:
            status = "Recuperação"

        else:
            status = "Reprovado"

        # ================================
        # RESULTADO FINAL
        # ================================
        boletim.append({
            "disciplina": disciplina.nome,
            "disciplina_id": disciplina.id,
            "bimestres": bimestres,
            "notas": notas_detalhadas,
            "media_final": media_final,
            "faltas": faltas_por_disciplina.get(disciplina.id, 0),
            "status": status
        })

    return boletim
