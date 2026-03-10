from django.db import transaction

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from home.models import (
    Docente,
    Turma,
    TurmaDisciplina,
    Disciplina,
    DiarioDeClasse,
    Chamada,
    Presenca,
    Aluno,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def salvar_chamada_api(request):
    user = request.user

    if user.role != "professor":
        return Response({
            "ok": False,
            "erro": "Apenas professores podem realizar chamada."
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
    disciplina_id = data.get("disciplina_id")
    data_ministrada = data.get("data_ministrada")
    resumo_conteudo = (data.get("resumo_conteudo") or "").strip()
    hora_inicio = data.get("hora_inicio")
    hora_fim = data.get("hora_fim")
    status_aula = (data.get("status") or "REALIZADA").strip()
    presencas = data.get("presencas", [])

    if not turma_id or not disciplina_id or not data_ministrada:
        return Response({
            "ok": False,
            "erro": "turma_id, disciplina_id e data_ministrada são obrigatórios."
        }, status=status.HTTP_400_BAD_REQUEST)

    if not resumo_conteudo:
        return Response({
            "ok": False,
            "erro": "O resumo do conteúdo é obrigatório."
        }, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(presencas, list) or len(presencas) == 0:
        return Response({
            "ok": False,
            "erro": "A lista de presenças é obrigatória."
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        turma = Turma.objects.get(id=turma_id, escola=user.escola)
    except Turma.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Turma não encontrada."
        }, status=status.HTTP_404_NOT_FOUND)

    try:
        disciplina = Disciplina.objects.get(id=disciplina_id, escola=user.escola)
    except Disciplina.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Disciplina não encontrada."
        }, status=status.HTTP_404_NOT_FOUND)

    possui_vinculo = TurmaDisciplina.objects.filter(
        turma=turma,
        disciplina=disciplina,
        professor=docente,
        escola=user.escola
    ).exists()

    if not possui_vinculo:
        return Response({
            "ok": False,
            "erro": "Você não tem permissão para lançar chamada nesta turma/disciplina."
        }, status=status.HTTP_403_FORBIDDEN)

    status_validos = {"PLANEJADA", "REALIZADA", "CANCELADA", "INVALIDA"}
    if status_aula not in status_validos:
        return Response({
            "ok": False,
            "erro": "Status inválido."
        }, status=status.HTTP_400_BAD_REQUEST)

    alunos_ids_turma = set(
        turma.alunos.filter(escola=user.escola).values_list("id", flat=True)
    )

    presencas_tratadas = []
    for item in presencas:
        aluno_id = item.get("aluno_id")
        status_presenca = (item.get("status") or "P").strip()
        observacao = (item.get("observacao") or "").strip()

        if not aluno_id:
            return Response({
                "ok": False,
                "erro": "Todos os registros de presença precisam de aluno_id."
            }, status=status.HTTP_400_BAD_REQUEST)

        if aluno_id not in alunos_ids_turma:
            return Response({
                "ok": False,
                "erro": f"O aluno {aluno_id} não pertence à turma."
            }, status=status.HTTP_400_BAD_REQUEST)

        if status_presenca not in {"P", "F", "J"}:
            return Response({
                "ok": False,
                "erro": f"Status de presença inválido para o aluno {aluno_id}."
            }, status=status.HTTP_400_BAD_REQUEST)

        presencas_tratadas.append({
            "aluno_id": aluno_id,
            "status": status_presenca,
            "observacao": observacao
        })

    with transaction.atomic():
        diario = DiarioDeClasse.objects.create(
            turma=turma,
            disciplina=disciplina,
            professor=docente,
            criado_por=user,
            data_ministrada=data_ministrada,
            hora_inicio=hora_inicio or None,
            hora_fim=hora_fim or None,
            resumo_conteudo=resumo_conteudo,
            status=status_aula,
            escola=user.escola
        )

        chamada = Chamada.objects.create(
            diario=diario,
            criado_por=user
        )

        for item in presencas_tratadas:
            aluno = Aluno.objects.get(id=item["aluno_id"], escola=user.escola)

            Presenca.objects.create(
                chamada=chamada,
                aluno=aluno,
                status=item["status"],
                observacao=item["observacao"]
            )

    return Response({
        "ok": True,
        "mensagem": "Chamada realizada com sucesso.",
        "diario_id": diario.id,
        "chamada_id": chamada.id,
        "turma": turma.nome,
        "disciplina": disciplina.nome,
        "data_ministrada": str(diario.data_ministrada),
        "total_presencas": len(presencas_tratadas)
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def consultar_chamada_api(request):
    user = request.user

    if user.role != "professor":
        return Response({
            "ok": False,
            "erro": "Apenas professores podem consultar chamada."
        }, status=status.HTTP_403_FORBIDDEN)

    turma_id = request.query_params.get("turma_id")
    disciplina_id = request.query_params.get("disciplina_id")
    data_ministrada = request.query_params.get("data_ministrada")

    if not turma_id or not disciplina_id or not data_ministrada:
        return Response({
            "ok": False,
            "erro": "turma_id, disciplina_id e data_ministrada são obrigatórios."
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

    try:
        disciplina = Disciplina.objects.get(id=disciplina_id, escola=user.escola)
    except Disciplina.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Disciplina não encontrada."
        }, status=status.HTTP_404_NOT_FOUND)

    possui_vinculo = TurmaDisciplina.objects.filter(
        turma=turma,
        disciplina=disciplina,
        professor=docente,
        escola=user.escola
    ).exists()

    if not possui_vinculo:
        return Response({
            "ok": False,
            "erro": "Você não tem permissão para consultar chamada nesta turma/disciplina."
        }, status=status.HTTP_403_FORBIDDEN)

    diario = (
        DiarioDeClasse.objects
        .filter(
            turma=turma,
            disciplina=disciplina,
            professor=docente,
            escola=user.escola,
            data_ministrada=data_ministrada
        )
        .select_related("turma", "disciplina", "professor")
        .order_by("-id")
        .first()
    )

    if not diario:
        return Response({
            "ok": True,
            "existe": False,
            "mensagem": "Nenhuma chamada encontrada para os filtros informados."
        }, status=status.HTTP_200_OK)

    chamada = Chamada.objects.filter(diario=diario).first()

    presencas_data = []
    if chamada:
        presencas = (
            Presenca.objects
            .filter(chamada=chamada)
            .select_related("aluno")
            .order_by("aluno__nome")
        )

        for presenca in presencas:
            presencas_data.append({
                "presenca_id": presenca.id,
                "aluno_id": presenca.aluno.id,
                "nome": presenca.aluno.nome,
                "matricula": presenca.aluno.matricula,
                "status": presenca.status,
                "presente": presenca.presente,
                "observacao": presenca.observacao,
            })

    return Response({
        "ok": True,
        "existe": True,
        "turma": {
            "id": turma.id,
            "nome": turma.nome,
            "turno": turma.turno,
            "ano": turma.ano,
            "sala": turma.sala,
        },
        "disciplina": {
            "id": disciplina.id,
            "nome": disciplina.nome,
        },
        "diario": {
            "id": diario.id,
            "data_ministrada": str(diario.data_ministrada),
            "hora_inicio": str(diario.hora_inicio) if diario.hora_inicio else None,
            "hora_fim": str(diario.hora_fim) if diario.hora_fim else None,
            "resumo_conteudo": diario.resumo_conteudo,
            "status": diario.status,
            "criado_em": diario.criado_em.isoformat() if diario.criado_em else None,
            "atualizado_em": diario.atualizado_em.isoformat() if diario.atualizado_em else None,
        },
        "chamada": {
            "id": chamada.id if chamada else None,
        },
        "total_presencas": len(presencas_data),
        "presencas": presencas_data
    }, status=status.HTTP_200_OK)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def atualizar_chamada_api(request, diario_id):
    user = request.user

    if user.role != "professor":
        return Response({
            "ok": False,
            "erro": "Apenas professores podem atualizar chamada."
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        docente = Docente.objects.get(user=user, escola=user.escola)
    except Docente.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Docente não encontrado para este usuário."
        }, status=status.HTTP_404_NOT_FOUND)

    try:
        diario = DiarioDeClasse.objects.select_related("turma", "disciplina").get(
            id=diario_id,
            escola=user.escola,
            professor=docente
        )
    except DiarioDeClasse.DoesNotExist:
        return Response({
            "ok": False,
            "erro": "Diário não encontrado."
        }, status=status.HTTP_404_NOT_FOUND)

    possui_vinculo = TurmaDisciplina.objects.filter(
        turma=diario.turma,
        disciplina=diario.disciplina,
        professor=docente,
        escola=user.escola
    ).exists()

    if not possui_vinculo:
        return Response({
            "ok": False,
            "erro": "Você não tem permissão para atualizar esta chamada."
        }, status=status.HTTP_403_FORBIDDEN)

    data = request.data

    resumo_conteudo = (data.get("resumo_conteudo") or "").strip()
    hora_inicio = data.get("hora_inicio")
    hora_fim = data.get("hora_fim")
    status_aula = (data.get("status") or diario.status).strip()
    presencas = data.get("presencas", [])

    if not resumo_conteudo:
        return Response({
            "ok": False,
            "erro": "O resumo do conteúdo é obrigatório."
        }, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(presencas, list) or len(presencas) == 0:
        return Response({
            "ok": False,
            "erro": "A lista de presenças é obrigatória."
        }, status=status.HTTP_400_BAD_REQUEST)

    status_validos = {"PLANEJADA", "REALIZADA", "CANCELADA", "INVALIDA"}
    if status_aula not in status_validos:
        return Response({
            "ok": False,
            "erro": "Status inválido."
        }, status=status.HTTP_400_BAD_REQUEST)

    chamada = Chamada.objects.filter(diario=diario).first()
    if not chamada:
        return Response({
            "ok": False,
            "erro": "Chamada não encontrada para este diário."
        }, status=status.HTTP_404_NOT_FOUND)

    alunos_ids_turma = set(
        diario.turma.alunos.filter(escola=user.escola).values_list("id", flat=True)
    )

    with transaction.atomic():
        diario.resumo_conteudo = resumo_conteudo
        diario.hora_inicio = hora_inicio or None
        diario.hora_fim = hora_fim or None
        diario.status = status_aula
        diario.criado_por = user
        diario.save()

        for item in presencas:
            aluno_id = item.get("aluno_id")
            status_presenca = (item.get("status") or "P").strip()
            observacao = (item.get("observacao") or "").strip()

            if not aluno_id:
                return Response({
                    "ok": False,
                    "erro": "Todos os registros de presença precisam de aluno_id."
                }, status=status.HTTP_400_BAD_REQUEST)

            if aluno_id not in alunos_ids_turma:
                return Response({
                    "ok": False,
                    "erro": f"O aluno {aluno_id} não pertence à turma."
                }, status=status.HTTP_400_BAD_REQUEST)

            if status_presenca not in {"P", "F", "J"}:
                return Response({
                    "ok": False,
                    "erro": f"Status de presença inválido para o aluno {aluno_id}."
                }, status=status.HTTP_400_BAD_REQUEST)

            aluno = Aluno.objects.get(id=aluno_id, escola=user.escola)

            presenca, _ = Presenca.objects.get_or_create(
                chamada=chamada,
                aluno=aluno,
                defaults={
                    "status": status_presenca,
                    "observacao": observacao,
                }
            )

            presenca.status = status_presenca
            presenca.observacao = observacao
            presenca.save()

    return Response({
        "ok": True,
        "mensagem": "Chamada atualizada com sucesso.",
        "diario_id": diario.id,
        "chamada_id": chamada.id,
        "turma": diario.turma.nome,
        "disciplina": diario.disciplina.nome,
        "data_ministrada": str(diario.data_ministrada),
        "total_presencas": len(presencas)
    }, status=status.HTTP_200_OK)