from django.db import transaction

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from home.models import (
    Docente,
    Turma,
    TurmaDisciplina,
    Avaliacao,
    Nota,
    Aluno,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def listar_avaliacoes_api(request):
    user = request.user

    if user.role != "professor":
        return Response({
            "ok": False,
            "erro": "Apenas professores podem consultar avaliações."
        }, status=status.HTTP_403_FORBIDDEN)

    turma_id = request.query_params.get("turma_id")
    disciplina_id = request.query_params.get("disciplina_id")
    bimestre = request.query_params.get("bimestre")

    if not turma_id or not disciplina_id or not bimestre:
        return Response({
            "ok": False,
            "erro": "turma_id, disciplina_id e bimestre são obrigatórios."
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        docente = Docente.objects.get(user=user, escola=user.escola)
    except Docente.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Docente não encontrado para este usuário."
        }, status=status.HTTP_404_NOT_FOUND)

    try:
        turma = Turma.objects.get(id=turma_id, escola=user.escola)
    except Turma.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Turma não encontrada."
        }, status=status.HTTP_404_NOT_FOUND)

    possui_vinculo = TurmaDisciplina.objects.filter(
        turma=turma,
        disciplina_id=disciplina_id,
        professor=docente,
        escola=user.escola
    ).exists()

    if not possui_vinculo:
        return Response({
            "ok": False,
            "erro": "Você não tem permissão para acessar avaliações desta turma/disciplina."
        }, status=status.HTTP_403_FORBIDDEN)

    avaliacoes = (
        Avaliacao.objects
        .filter(
            disciplina_id=disciplina_id,
            bimestre=bimestre,
            escola=user.escola
        )
        .select_related("tipo", "disciplina")
        .order_by("data", "id")
    )

    avaliacoes_data = []
    for avaliacao in avaliacoes:
        avaliacoes_data.append({
            "id": avaliacao.id,
            "descricao": avaliacao.descricao,
            "disciplina_id": avaliacao.disciplina.id,
            "disciplina_nome": avaliacao.disciplina.nome,
            "tipo_id": avaliacao.tipo.id,
            "tipo_nome": avaliacao.tipo.nome,
            "peso": float(avaliacao.tipo.peso),
            "bimestre": avaliacao.bimestre,
            "data": str(avaliacao.data),
        })

    return Response({
        "ok": True,
        "turma": {
            "id": turma.id,
            "nome": turma.nome,
            "turno": turma.turno,
            "ano": turma.ano,
            "sala": turma.sala,
            "sistema_avaliacao": turma.sistema_avaliacao,
        },
        "disciplina_id": int(disciplina_id),
        "bimestre": int(bimestre),
        "total_avaliacoes": len(avaliacoes_data),
        "avaliacoes": avaliacoes_data,
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def consultar_notas_api(request):
    user = request.user

    if user.role != "professor":
        return Response({
            "ok": False,
            "erro": "Apenas professores podem consultar notas."
        }, status=status.HTTP_403_FORBIDDEN)

    turma_id = request.query_params.get("turma_id")
    disciplina_id = request.query_params.get("disciplina_id")
    bimestre = request.query_params.get("bimestre")

    if not turma_id or not disciplina_id or not bimestre:
        return Response({
            "ok": False,
            "erro": "turma_id, disciplina_id e bimestre são obrigatórios."
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        docente = Docente.objects.get(user=user, escola=user.escola)
    except Docente.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Docente não encontrado para este usuário."
        }, status=status.HTTP_404_NOT_FOUND)

    try:
        turma = Turma.objects.get(id=turma_id, escola=user.escola)
    except Turma.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Turma não encontrada."
        }, status=status.HTTP_404_NOT_FOUND)

    possui_vinculo = TurmaDisciplina.objects.filter(
        turma=turma,
        disciplina_id=disciplina_id,
        professor=docente,
        escola=user.escola
    ).exists()

    if not possui_vinculo:
        return Response({
            "ok": False,
            "erro": "Você não tem permissão para acessar notas desta turma/disciplina."
        }, status=status.HTTP_403_FORBIDDEN)

    avaliacoes = list(
        Avaliacao.objects.filter(
            disciplina_id=disciplina_id,
            bimestre=bimestre,
            escola=user.escola
        )
        .select_related("tipo", "disciplina")
        .order_by("data", "id")
    )

    alunos = list(
        turma.alunos.filter(escola=user.escola, ativo=True).order_by("nome")
    )

    notas_qs = Nota.objects.filter(
        aluno__in=alunos,
        avaliacao__in=avaliacoes,
        escola=user.escola
    ).select_related("aluno", "avaliacao")

    notas_map = {}
    for nota in notas_qs:
        chave = (nota.aluno_id, nota.avaliacao_id)
        notas_map[chave] = {
            "nota_id": nota.id,
            "valor": float(nota.valor) if nota.valor is not None else None,
            "conceito": nota.conceito,
        }

    avaliacoes_data = []
    for avaliacao in avaliacoes:
        avaliacoes_data.append({
            "id": avaliacao.id,
            "descricao": avaliacao.descricao,
            "tipo_id": avaliacao.tipo.id,
            "tipo_nome": avaliacao.tipo.nome,
            "peso": float(avaliacao.tipo.peso),
            "data": str(avaliacao.data),
            "bimestre": avaliacao.bimestre,
        })

    alunos_data = []
    for aluno in alunos:
        notas_aluno = []

        for avaliacao in avaliacoes:
            nota_info = notas_map.get((aluno.id, avaliacao.id), {
                "nota_id": None,
                "valor": None,
                "conceito": None,
            })

            notas_aluno.append({
                "avaliacao_id": avaliacao.id,
                "descricao": avaliacao.descricao,
                "nota_id": nota_info["nota_id"],
                "valor": nota_info["valor"],
                "conceito": nota_info["conceito"],
            })

        alunos_data.append({
            "id": aluno.id,
            "matricula": aluno.matricula,
            "nome": aluno.nome,
            "notas": notas_aluno,
        })

    return Response({
        "ok": True,
        "turma": {
            "id": turma.id,
            "nome": turma.nome,
            "turno": turma.turno,
            "ano": turma.ano,
            "sala": turma.sala,
            "sistema_avaliacao": turma.sistema_avaliacao,
        },
        "disciplina_id": int(disciplina_id),
        "bimestre": int(bimestre),
        "avaliacoes": avaliacoes_data,
        "total_alunos": len(alunos_data),
        "alunos": alunos_data,
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def salvar_notas_api(request):
    user = request.user

    if user.role != "professor":
        return Response({
            "ok": False,
            "erro": "Apenas professores podem lançar notas."
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        docente = Docente.objects.get(user=user, escola=user.escola)
    except Docente.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Docente não encontrado para este usuário."
        }, status=status.HTTP_404_NOT_FOUND)

    data = request.data

    turma_id = data.get("turma_id")
    avaliacao_id = data.get("avaliacao_id")
    notas = data.get("notas", [])

    if not turma_id or not avaliacao_id:
        return Response({
            "ok": False,
            "erro": "turma_id e avaliacao_id são obrigatórios."
        }, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(notas, list) or len(notas) == 0:
        return Response({
            "ok": False,
            "erro": "A lista de notas é obrigatória."
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        turma = Turma.objects.get(id=turma_id, escola=user.escola)
    except Turma.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Turma não encontrada."
        }, status=status.HTTP_404_NOT_FOUND)

    try:
        avaliacao = Avaliacao.objects.select_related("disciplina").get(
            id=avaliacao_id,
            escola=user.escola
        )
    except Avaliacao.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Avaliação não encontrada."
        }, status=status.HTTP_404_NOT_FOUND)

    possui_vinculo = TurmaDisciplina.objects.filter(
        turma=turma,
        disciplina=avaliacao.disciplina,
        professor=docente,
        escola=user.escola
    ).exists()

    if not possui_vinculo:
        return Response({
            "ok": False,
            "erro": "Você não tem permissão para lançar notas nesta turma/disciplina."
        }, status=status.HTTP_403_FORBIDDEN)

    alunos_ids_turma = set(
        turma.alunos.filter(escola=user.escola, ativo=True).values_list("id", flat=True)
    )

    sistema_avaliacao = turma.sistema_avaliacao
    conceitos_validos = {"E", "O", "B"}

    notas_tratadas = []

    for item in notas:
        aluno_id = item.get("aluno_id")
        valor = item.get("valor")
        conceito = item.get("conceito")

        if not aluno_id:
            return Response({
                "ok": False,
                "erro": "Todos os registros precisam de aluno_id."
            }, status=status.HTTP_400_BAD_REQUEST)

        if aluno_id not in alunos_ids_turma:
            return Response({
                "ok": False,
                "erro": f"O aluno {aluno_id} não pertence à turma."
            }, status=status.HTTP_400_BAD_REQUEST)

        if sistema_avaliacao == "NUM":
            if valor in ("", None):
                return Response({
                    "ok": False,
                    "erro": f"Informe a nota numérica do aluno {aluno_id}."
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                valor_float = float(valor)
            except (TypeError, ValueError):
                return Response({
                    "ok": False,
                    "erro": f"Nota inválida para o aluno {aluno_id}."
                }, status=status.HTTP_400_BAD_REQUEST)

            conceito = None
            valor = valor_float

        elif sistema_avaliacao == "CON":
            if not conceito or conceito not in conceitos_validos:
                return Response({
                    "ok": False,
                    "erro": f"Conceito inválido para o aluno {aluno_id}. Use E, O ou B."
                }, status=status.HTTP_400_BAD_REQUEST)

            valor = None

        notas_tratadas.append({
            "aluno_id": aluno_id,
            "valor": valor,
            "conceito": conceito,
        })

    criadas = 0
    atualizadas = 0

    with transaction.atomic():
        for item in notas_tratadas:
            aluno = Aluno.objects.get(id=item["aluno_id"], escola=user.escola)

            nota, created = Nota.objects.get_or_create(
                aluno=aluno,
                avaliacao=avaliacao,
                defaults={
                    "valor": item["valor"],
                    "conceito": item["conceito"],
                    "escola": user.escola,
                }
            )

            if created:
                criadas += 1
            else:
                nota.valor = item["valor"]
                nota.conceito = item["conceito"]
                nota.escola = user.escola
                nota.save()
                atualizadas += 1

    return Response({
        "ok": True,
        "mensagem": "Notas salvas com sucesso.",
        "turma": turma.nome,
        "disciplina": avaliacao.disciplina.nome,
        "avaliacao": avaliacao.descricao,
        "sistema_avaliacao": sistema_avaliacao,
        "total_recebidas": len(notas_tratadas),
        "criadas": criadas,
        "atualizadas": atualizadas,
    }, status=status.HTTP_200_OK)