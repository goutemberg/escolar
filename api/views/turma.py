from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from home.models import (
    Docente,
    Turma,
    TurmaDisciplina,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def minhas_turmas(request):
    user = request.user

    if user.role != "professor":
        return Response({
            "ok": False,
            "erro": "Apenas professores podem acessar este endpoint."
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        docente = Docente.objects.get(user=user, escola=user.escola)
    except Docente.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Docente não encontrado para este usuário."
        }, status=status.HTTP_404_NOT_FOUND)

    vinculos = (
        TurmaDisciplina.objects
        .filter(
            professor=docente,
            escola=user.escola
        )
        .select_related("turma", "disciplina")
        .order_by("turma__nome", "disciplina__nome")
    )

    turmas_map = {}

    for vinculo in vinculos:
        turma = vinculo.turma

        if turma.id not in turmas_map:
            turmas_map[turma.id] = {
                "id": turma.id,
                "nome": turma.nome,
                "turno": turma.turno,
                "ano": turma.ano,
                "sala": turma.sala,
                "sistema_avaliacao": turma.sistema_avaliacao,
                "disciplinas": []
            }

        turmas_map[turma.id]["disciplinas"].append({
            "id": vinculo.disciplina.id,
            "nome": vinculo.disciplina.nome
        })

    return Response({
        "ok": True,
        "professor": docente.nome,
        "turmas": list(turmas_map.values())
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alunos_da_turma(request, turma_id):
    user = request.user

    if user.role != "professor":
        return Response({
            "ok": False,
            "erro": "Apenas professores podem acessar este endpoint."
        }, status=status.HTTP_403_FORBIDDEN)

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
        professor=docente,
        escola=user.escola
    ).exists()

    if not possui_vinculo:
        return Response({
            "ok": False,
            "erro": "Você não tem permissão para acessar esta turma."
        }, status=status.HTTP_403_FORBIDDEN)

    alunos = turma.alunos.filter(
        escola=user.escola
    ).order_by("nome")

    alunos_data = []
    for aluno in alunos:
        alunos_data.append({
            "id": aluno.id,
            "matricula": aluno.matricula,
            "nome": aluno.nome,
            "cpf": aluno.cpf,
            "ativo": aluno.ativo,
            "turma_principal_id": aluno.turma_principal_id,
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
        "total_alunos": len(alunos_data),
        "alunos": alunos_data
    }, status=status.HTTP_200_OK)