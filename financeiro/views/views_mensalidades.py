from django.shortcuts import render, redirect
from financeiro.models import Mensalidade
from django.http import JsonResponse
from django.utils import timezone
from home.models import Aluno, Turma
from django.contrib import messages
from datetime import date
from decimal import Decimal
import calendar


def listar_mensalidades(request):

    escola = request.user.escola

    mensalidades = Mensalidade.objects.filter(
        escola=escola
    ).select_related('aluno').order_by('-vencimento')

    context = {
        "mensalidades": mensalidades,
        "today": date.today()
    }

    return render(
        request,
        "financeiro/listar_mensalidades.html",
        context
    )

def dar_baixa_mensalidade(request, mensalidade_id):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:

        mensalidade = Mensalidade.objects.get(
            id=mensalidade_id,
            escola=request.user.escola
        )

        mensalidade.status = "pago"
        mensalidade.pago_em = timezone.now()
        mensalidade.save()

        return JsonResponse({"success": True})

    except Mensalidade.DoesNotExist:

        return JsonResponse({
            "success": False,
            "error": "Mensalidade não encontrada"
        }, status=404)


def gerar_mensalidades(request):

    escola = request.user.escola

    turmas = Turma.objects.filter(escola=escola)

    if request.method == "POST":

        turma_id = request.POST.get("turma_id")
        mes_inicio = int(request.POST.get("mes_inicio"))
        mes_fim = int(request.POST.get("mes_fim"))
        ano = int(request.POST.get("ano"))
        valor = Decimal(request.POST.get("valor"))
        dia_vencimento = int(request.POST.get("dia_vencimento"))

        # valida meses
        if mes_inicio < 1 or mes_inicio > 12 or mes_fim < 1 or mes_fim > 12:
            messages.error(request, "Os meses devem estar entre 1 e 12.")
            return redirect("gerar_mensalidades")

        if mes_fim < mes_inicio:
            messages.error(request, "Mês final não pode ser menor que o mês inicial.")
            return redirect("gerar_mensalidades")

        try:
            turma = Turma.objects.get(id=turma_id, escola=escola)
        except Turma.DoesNotExist:
            messages.error(request, "Turma não encontrada.")
            return redirect("gerar_mensalidades")

        alunos = Aluno.objects.filter(
            turma_principal=turma,
            escola=escola,
            ativo=True
        )

        criadas = 0
        ignoradas = 0

        # percorre os meses
        for mes in range(mes_inicio, mes_fim + 1):

            ultimo_dia = calendar.monthrange(ano, mes)[1]
            dia = min(dia_vencimento, ultimo_dia)

            for aluno in alunos:

                vencimento = date(ano, mes, dia)

                # -------------------------------
                # DESCONTO AUTOMÁTICO DO ALUNO
                # -------------------------------
                desconto_auto = aluno.desconto_mensal or Decimal("0.00")

                valor_final = valor - desconto_auto

                # evita valor negativo
                if valor_final < 0:
                    valor_final = Decimal("0.00")

                mensalidade, created = Mensalidade.objects.get_or_create(

                    aluno=aluno,
                    mes_referencia=mes,
                    ano_referencia=ano,

                    defaults={

                        "escola": escola,

                        "valor_original": valor,
                        "desconto": desconto_auto,
                        "valor_final": valor_final,

                        "vencimento": vencimento,

                        "status": "pendente"

                    }
                )

                if created:
                    criadas += 1
                else:
                    ignoradas += 1

        messages.success(
            request,
            f"{criadas} mensalidades geradas. {ignoradas} já existiam."
        )

        return redirect("listar_mensalidades")

    return render(
        request,
        "financeiro/gerar_mensalidades.html",
        {"turmas": turmas}
    )