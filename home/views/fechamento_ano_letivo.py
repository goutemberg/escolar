from django.shortcuts import render
from django.utils import timezone
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone

from home.models import (
    AnoLetivo,
    Turma,
    FechamentoAnoLog,
    AuditLog,
    Avaliacao,
    Nota,
)

from home.utils import get_client_ip


# =====================================================
# FECHAR ANO LETIVO (SAP LEVEL FINAL)
# =====================================================
@login_required
@require_POST
def fechar_ano_letivo(request):

    # 🔒 PERMISSÃO
    if not request.user.has_role("diretor"):
        return JsonResponse({"error": "Sem permissão"}, status=403)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    ano_id = data.get("ano_id")

    ano = AnoLetivo.objects.filter(id=ano_id).first()

    if not ano:
        return JsonResponse({"error": "Ano não encontrado"}, status=404)

    if ano.encerrado:
        return JsonResponse({"error": "Ano já encerrado"}, status=400)

    # 🔥 SNAPSHOT ANTES (SAP LEVEL)
    antes = {
        "ano": ano.ano,
        "ativo": ano.ativo,
        "encerrado": ano.encerrado,
        "data_fim": str(ano.data_fim)
    }

    try:
        with transaction.atomic():

            # =================================================
            # 🔒 FECHAMENTO PRINCIPAL
            # =================================================
            ano.ativo = False
            ano.encerrado = True
            ano.data_fim = timezone.now().date()
            ano.fechado_em = timezone.now()
            ano.fechado_por = request.user
            ano.save()

            # =================================================
            # 🔒 IMPACTO SISTÊMICO
            # =================================================
            Turma.objects.filter(ano_letivo=ano).update(status="INATIVA")

            # =================================================
            # 🔥 LOG DE FECHAMENTO (SIMPLES)
            # =================================================
            FechamentoAnoLog.objects.create(
                ano=ano,
                usuario=request.user,
                escola=request.escola,
                acao="FECHAMENTO",
                detalhes=f"Ano {ano.ano} encerrado com sucesso",
                ip=get_client_ip(request)
            )

            # =================================================
            # 🔥 AUDITORIA SAP (COMPLETA)
            # =================================================
            AuditLog.objects.create(
                user=request.user,
                escola=request.escola,
                acao="FECHAMENTO_ANO",
                modelo="AnoLetivo",
                objeto_id=str(ano.id),
                antes=antes,
                depois={
                    "ano": ano.ano,
                    "ativo": False,
                    "encerrado": True,
                    "data_fim": str(ano.data_fim)
                },
                ip=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")
            )

        return JsonResponse({
            "success": True,
            "mensagem": f"Ano {ano.ano} fechado com sucesso (SAP MODE)"
        })

    except Exception as e:

        # 🔥 LOG DE FALHA (NÍVEL SAP)
        FechamentoAnoLog.objects.create(
            ano=ano,
            usuario=request.user,
            escola=request.escola,
            acao="FECHAMENTO_FALHA",
            detalhes=str(e),
            ip=get_client_ip(request)
        )

        return JsonResponse({"error": str(e)}, status=500)


# =====================================================
# TELA DE FECHAMENTO
# =====================================================
@login_required
def tela_fechamento_ano(request):

    ano = AnoLetivo.objects.filter(ativo=True).first()

    return render(request, "pages/fechar_ano_letivo.html", {
        "ano": ano,
        "total_turmas": Turma.objects.filter(ano_letivo=ano).count(),
        "total_avaliacoes": Avaliacao.objects.filter(ano_letivo=ano).count(),
        "total_notas": Nota.objects.filter(avaliacao__ano_letivo=ano).count(),
    })


# =====================================================
# REABERTURA DE ANO (SAP CONTROLADO)
# =====================================================
@login_required
@require_POST
def reabrir_ano_letivo(request):

    if not request.user.has_role("diretor"):
        return JsonResponse({"error": "Sem permissão"}, status=403)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    ano_id = data.get("ano_id")

    ano = AnoLetivo.objects.filter(id=ano_id).first()

    if not ano:
        return JsonResponse({"error": "Ano não encontrado"}, status=404)

    if not ano.encerrado:
        return JsonResponse({"error": "Ano não está encerrado"}, status=400)

    try:
        with transaction.atomic():

            ano.encerrado = False
            ano.ativo = True
            ano.data_fim = None
            ano.fechado_em = None
            ano.fechado_por = None
            ano.save()

            # =====================================================
            # REATIVA TURMAS DO ANO
            # =====================================================
            Turma.objects.filter(
                ano_letivo=ano
            ).update(status="ATIVA")

            FechamentoAnoLog.objects.create(
                ano=ano,
                usuario=request.user,
                escola=request.escola,
                acao="REABERTURA",
                detalhes=f"Ano {ano.ano} reaberto",
                ip=get_client_ip(request)
            )

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)