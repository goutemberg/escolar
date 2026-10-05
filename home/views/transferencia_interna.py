import json

from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from home.decorators import role_required
from home.models import (
    Aluno,
    HistoricoAlocacaoAluno,
    Matricula,
    Turma,
)
from home.utils import get_ano_ativo


@login_required
@role_required(["diretor", "coordenador"])
def transferencia_interna(request):

    escola = request.escola
    ano_ativo = get_ano_ativo()

    alunos = []
    turmas = []

    if ano_ativo:

        alunos = (
            Aluno.objects.filter(
                escola=escola,
                ativo=True,
                turma_principal__isnull=False,
            )
            .select_related(
                "turma_principal",
            )
            .distinct()
            .order_by("nome")
        )

        turmas = Turma.objects.filter(
            escola=escola,
            ano_letivo=ano_ativo,
            status="ATIVA",
        ).order_by("nome")

    context = {
        "ano_ativo": ano_ativo,
        "alunos": alunos,
        "turmas": turmas,
    }

    return render(
        request,
        "pages/transferencia_interna.html",
        context,
    )


@login_required
@role_required(["diretor", "coordenador"])
def dados_aluno_transferencia(request, aluno_id):

    escola = request.escola
    ano_ativo = get_ano_ativo()

    if not ano_ativo:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Não existe um ano letivo ativo.",
            },
            status=400,
        )

    aluno = get_object_or_404(
        Aluno.objects.select_related(
            "turma_principal",
        ),
        id=aluno_id,
        escola=escola,
        ativo=True,
    )

    matricula = (
        Matricula.objects.filter(
            aluno=aluno,
            ano_letivo=ano_ativo,
            status="ATIVA",
        )
        .select_related(
            "turma",
            "ano_letivo",
        )
        .first()
    )

    turmas = Turma.objects.filter(
        escola=escola,
        ano_letivo=ano_ativo,
        status="ATIVA",
    ).order_by("nome")

    turmas_disponiveis = [
        {
            "id": turma.id,
            "nome": turma.nome,
            "turno": turma.turno,
        }
        for turma in turmas
    ]

    return JsonResponse(
        {
            "success": True,
            "aluno": {
                "id": aluno.id,
                "nome": aluno.nome,
                "matricula": aluno.matricula,
                "turma_atual": (
                    aluno.turma_principal.nome if aluno.turma_principal else None
                ),
                "turma_atual_id": (
                    aluno.turma_principal.id if aluno.turma_principal else None
                ),
                "turno_atual": aluno.turno_aluno,
            },
            "matricula": (
                {
                    "id": matricula.id,
                    "ano_letivo": matricula.ano_letivo.ano,
                    "turma_id": (matricula.turma.id if matricula.turma else None),
                }
                if matricula
                else None
            ),
            "turmas": turmas_disponiveis,
        }
    )


@login_required
@role_required(["diretor", "coordenador"])
@require_POST
def salvar_transferencia_interna(request):

    escola = request.escola
    ano_ativo = get_ano_ativo()

    if not ano_ativo:
        return JsonResponse(
            {
                "success": False,
                "mensagem": (
                    "Não existe um ano letivo ativo " "para realizar a transferência."
                ),
            },
            status=400,
        )

    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Dados da transferência inválidos.",
            },
            status=400,
        )

    aluno_id = data.get("aluno_id")
    nova_turma_id = data.get("nova_turma_id")
    novo_turno = (data.get("novo_turno") or "").strip()
    data_transferencia = (data.get("data_transferencia") or "").strip()
    observacao = (data.get("observacao") or "").strip()

    # ==========================================================
    # VALIDAÇÕES BÁSICAS
    # ==========================================================

    if not aluno_id:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Selecione o aluno.",
            },
            status=400,
        )

    if not nova_turma_id:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Selecione a nova turma.",
            },
            status=400,
        )

    if not novo_turno:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Selecione o novo turno.",
            },
            status=400,
        )

    if not data_transferencia:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Informe a data da transferência.",
            },
            status=400,
        )

    try:
        data_transferencia = datetime.strptime(
            data_transferencia,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "A data da transferência é inválida.",
            },
            status=400,
        )

    # ==========================================================
    # DATA DENTRO DO ANO LETIVO
    # ==========================================================

    if ano_ativo.data_inicio and data_transferencia < ano_ativo.data_inicio:
        return JsonResponse(
            {
                "success": False,
                "mensagem": (
                    "A data da transferência não pode ser "
                    "anterior ao início do ano letivo."
                ),
            },
            status=400,
        )

    if ano_ativo.data_fim and data_transferencia > ano_ativo.data_fim:
        return JsonResponse(
            {
                "success": False,
                "mensagem": (
                    "A data da transferência não pode ser "
                    "posterior ao fim do ano letivo."
                ),
            },
            status=400,
        )

    # ==========================================================
    # TRANSAÇÃO
    # ==========================================================

    with transaction.atomic():

        # ------------------------------------------------------
        # ALUNO
        # ------------------------------------------------------

        aluno = get_object_or_404(
            Aluno.objects.select_for_update(),
            id=aluno_id,
            escola=escola,
            ativo=True,
        )

        # ------------------------------------------------------
        # MATRÍCULA ATIVA — OPCIONAL PARA ALUNOS LEGADOS
        # ------------------------------------------------------

        matricula = (
            Matricula.objects.select_for_update()
            .filter(
                aluno=aluno,
                ano_letivo=ano_ativo,
                status="ATIVA",
            )
            .first()
        )

        # ------------------------------------------------------
        # TURMA DESTINO
        # ------------------------------------------------------

        nova_turma = Turma.objects.filter(
            id=nova_turma_id,
            escola=escola,
            ano_letivo=ano_ativo,
            status="ATIVA",
        ).first()

        if not nova_turma:
            return JsonResponse(
                {
                    "success": False,
                    "mensagem": (
                        "A turma selecionada não está disponível "
                        "para este ano letivo."
                    ),
                },
                status=404,
            )

        # ------------------------------------------------------
        # ESTADO ATUAL
        # ------------------------------------------------------

        turma_atual = aluno.turma_principal
        turno_atual = (aluno.turno_aluno or "").strip()

        if not turma_atual:
            return JsonResponse(
                {
                    "success": False,
                    "mensagem": (
                        "O aluno não possui uma turma principal "
                        "definida para realizar a transferência."
                    ),
                },
                status=400,
            )

        # ------------------------------------------------------
        # IMPEDIR TRANSFERÊNCIA SEM ALTERAÇÃO
        # ------------------------------------------------------

        mesma_turma = turma_atual.id == nova_turma.id
        mesmo_turno = turno_atual == novo_turno

        if mesma_turma and mesmo_turno:
            return JsonResponse(
                {
                    "success": False,
                    "mensagem": (
                        "A nova turma e o novo turno são iguais "
                        "à alocação atual do aluno."
                    ),
                },
                status=400,
            )

        # ======================================================
        # IDENTIFICAR TIPO DE MOVIMENTAÇÃO
        # ======================================================

        if not mesma_turma and mesmo_turno:
            tipo_movimentacao = (
                HistoricoAlocacaoAluno.TipoMovimentacao.TRANSFERENCIA_TURMA
            )

        elif mesma_turma and not mesmo_turno:
            tipo_movimentacao = HistoricoAlocacaoAluno.TipoMovimentacao.ALTERACAO_TURNO

        else:
            tipo_movimentacao = (
                HistoricoAlocacaoAluno.TipoMovimentacao.TRANSFERENCIA_TURMA_TURNO
            )

        # ======================================================
        # HISTÓRICO ANTERIOR
        # ======================================================

        historico_aberto = (
            HistoricoAlocacaoAluno.objects.select_for_update()
            .filter(
                aluno=aluno,
                ano_letivo=ano_ativo,
                data_fim__isnull=True,
            )
            .order_by(
                "-data_inicio",
                "-criado_em",
            )
            .first()
        )

        if historico_aberto:

            historico_aberto.data_fim = data_transferencia

            historico_aberto.save(update_fields=["data_fim"])

        else:

            # Primeiro movimento do aluno.
            #
            # Para alunos legados que não possuem matrícula,
            # usamos o início do ano letivo como referência,
            # pois não temos uma data histórica confiável
            # de matrícula/alocação.

            HistoricoAlocacaoAluno.objects.create(
                aluno=aluno,
                ano_letivo=ano_ativo,
                turma=turma_atual,
                turno=turno_atual,
                data_inicio=(
                    matricula.data_matricula
                    if matricula and matricula.data_matricula
                    else ano_ativo.data_inicio
                ),
                data_fim=data_transferencia,
                tipo_movimentacao=(HistoricoAlocacaoAluno.TipoMovimentacao.MATRICULA),
                realizado_por=request.user,
                observacao=(
                    "Registro inicial da alocação "
                    "antes da primeira transferência interna."
                ),
            )

        # ======================================================
        # NOVA ALOCAÇÃO NO HISTÓRICO
        # ======================================================

        HistoricoAlocacaoAluno.objects.create(
            aluno=aluno,
            ano_letivo=ano_ativo,
            turma=nova_turma,
            turno=novo_turno,
            data_inicio=data_transferencia,
            data_fim=None,
            tipo_movimentacao=tipo_movimentacao,
            realizado_por=request.user,
            observacao=observacao,
        )

        # ======================================================
        # ATUALIZAR MATRÍCULA — SOMENTE SE EXISTIR
        # ======================================================

        if matricula:
            matricula.turma = nova_turma

            matricula.save(
                update_fields=[
                    "turma",
                    "atualizado_em",
                ]
            )

        # ======================================================
        # ATUALIZAR ESTADO ATUAL DO ALUNO
        # ======================================================

        aluno.turma_principal = nova_turma
        aluno.turno_aluno = novo_turno

        aluno.save(
            update_fields=[
                "turma_principal",
                "turno_aluno",
            ]
        )

        # ======================================================
        # SINCRONIZAR M2M LEGADO
        # ======================================================

        aluno.turmas.set([nova_turma])

    return JsonResponse(
        {
            "success": True,
            "mensagem": (
                f"Transferência interna de " f"{aluno.nome} realizada com sucesso."
            ),
            "aluno": {
                "id": aluno.id,
                "nome": aluno.nome,
                "matricula": aluno.matricula,
            },
            "turma_anterior": turma_atual.nome,
            "turma_nova": nova_turma.nome,
            "turno_anterior": turno_atual,
            "turno_novo": novo_turno,
            "data_transferencia": (data_transferencia.strftime("%Y-%m-%d")),
        },
        status=200,
    )
