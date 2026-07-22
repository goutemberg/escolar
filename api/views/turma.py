from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from home.models import (
    Docente,
    Turma,
    TurmaDisciplina,
    DiarioDeClasse,
    Presenca,
    Chamada,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def minhas_turmas(request):
    user = request.user

    # Apenas Professor, Coordenador e Diretor podem acessar
    if user.role not in ["professor", "coordenador", "diretor"]:
        return Response(
            {"ok": False, "erro": "Sem permissão para acessar este endpoint."},
            status=status.HTTP_403_FORBIDDEN,
        )

    professor_nome = None

    # Professor: apenas suas turmas
    if user.role == "professor":
        try:
            docente = Docente.objects.get(user=user, escola=user.escola)
            professor_nome = docente.nome
        except Docente.DoesNotExist:
            return Response(
                {
                    "ok": False,
                    "erro": "Docente não encontrado para este usuário.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        vinculos = (
            TurmaDisciplina.objects.filter(
                professor=docente,
                escola=user.escola,
            )
            .select_related("turma", "disciplina")
            .order_by("turma__nome", "disciplina__nome")
        )

    # Coordenador e Diretor: todas as turmas da escola
    else:
        professor_nome = user.nome if hasattr(user, "nome") else user.username

        vinculos = (
            TurmaDisciplina.objects.filter(
                escola=user.escola,
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
                "disciplinas": [],
            }

        # Evita disciplinas duplicadas
        if not any(
            d["id"] == vinculo.disciplina.id
            for d in turmas_map[turma.id]["disciplinas"]
        ):
            turmas_map[turma.id]["disciplinas"].append(
                {
                    "id": vinculo.disciplina.id,
                    "nome": vinculo.disciplina.nome,
                }
            )

    return Response(
        {
            "ok": True,
            "professor": professor_nome,
            "turmas": list(turmas_map.values()),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alunos_da_turma(request, turma_id):
    user = request.user

    # =====================================================
    # PERMISSÕES
    # =====================================================
    if user.role not in ["professor", "coordenador", "diretor"]:
        return Response(
            {
                "ok": False,
                "erro": "Sem permissão para acessar este endpoint.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    docente = None

    if user.role == "professor":
        try:
            docente = Docente.objects.get(
                user=user,
                escola=user.escola,
            )
        except Docente.DoesNotExist:
            return Response(
                {
                    "ok": False,
                    "erro": "Docente não encontrado para este usuário.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    try:
        turma = Turma.objects.get(
            id=turma_id,
            escola=user.escola,
        )
    except Turma.DoesNotExist:
        return Response(
            {
                "ok": False,
                "erro": "Turma não encontrada.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # =====================================================
    # PROFESSOR SÓ ACESSA SUAS TURMAS
    # =====================================================
    if user.role == "professor":

        possui_vinculo = TurmaDisciplina.objects.filter(
            turma=turma,
            professor=docente,
            escola=user.escola,
        ).exists()

        if not possui_vinculo:
            return Response(
                {
                    "ok": False,
                    "erro": "Você não tem permissão para acessar esta turma.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    # =====================================================
    # ALUNOS
    # =====================================================
    alunos = turma.alunos.filter(
        escola=user.escola,
        ativo=True,
    ).order_by("nome")

    data_aula = request.GET.get("data")
    disciplina_id = request.GET.get("disciplina")

    presencas_map = {}

    if data_aula and disciplina_id:

        # ==============================================
        # NOVO FLUXO
        # PROCURA A CHAMADA DIRETAMENTE
        # ==============================================
        chamada = (
            Chamada.objects.filter(
                escola=user.escola,
                turma=turma,
                disciplina_id=disciplina_id,
                data=data_aula,
            )
            .order_by("-id")
            .first()
        )

        # ==============================================
        # COMPATIBILIDADE COM REGISTROS ANTIGOS
        # ==============================================
        if not chamada:

            diario = (
                DiarioDeClasse.objects.filter(
                    escola=user.escola,
                    turma=turma,
                    disciplina_id=disciplina_id,
                    data_ministrada=data_aula,
                )
                .order_by("-id")
                .first()
            )

            if diario:
                chamada = (
                    Chamada.objects.filter(
                        diario=diario,
                    )
                    .order_by("-id")
                    .first()
                )

        if chamada:

            presencas = Presenca.objects.filter(
                chamada=chamada,
            )

            for p in presencas:

                status_presenca = p.status

                # Compatibilidade com registros antigos
                if not status_presenca:
                    status_presenca = "P" if p.presente else "F"

                presencas_map[p.aluno_id] = {
                    "status": status_presenca,
                    "observacao": p.observacao or "",
                }

    alunos_data = []

    for aluno in alunos:

        extra = presencas_map.get(aluno.id, {})

        alunos_data.append(
            {
                "id": aluno.id,
                "matricula": aluno.matricula,
                "nome": aluno.nome,
                "cpf": aluno.cpf,
                "ativo": aluno.ativo,
                "turma_principal_id": aluno.turma_principal_id,
                "status": extra.get("status", "P"),
                "observacao": extra.get("observacao", ""),
            }
        )

    return Response(
        {
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
            "alunos": alunos_data,
        },
        status=status.HTTP_200_OK,
    )
