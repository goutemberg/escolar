from django.shortcuts import render, redirect
from financeiro.models import Mensalidade
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from home.models import Aluno, Turma
from django.contrib import messages
from datetime import date
from decimal import Decimal
import calendar
import csv
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from openpyxl import Workbook
import json



def listar_mensalidades(request):

    escola = request.escola

    hoje = date.today()

    # =========================
    # FILTRO MÊS / ANO
    # =========================

    mes = request.GET.get("mes")
    ano = request.GET.get("ano")

    mes = int(mes) if mes else hoje.month
    ano = int(ano) if ano else hoje.year

    # =========================
    # MESES (PT-BR)
    # =========================

    meses_pt = [
        (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"),
        (4, "Abril"), (5, "Maio"), (6, "Junho"),
        (7, "Julho"), (8, "Agosto"), (9, "Setembro"),
        (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
    ]

    mes_nome = dict(meses_pt).get(mes)

    # =========================
    # QUERY BASE
    # =========================

    mensalidades = Mensalidade.objects.filter(
        escola=escola
    ).select_related('aluno').order_by('-vencimento')

    # 🔹 COMPETÊNCIA (mês referência)
    mensalidades_mes = mensalidades.filter(
        mes_referencia=mes,
        ano_referencia=ano
    )

    # =========================
    # CÁLCULOS (COMPETÊNCIA)
    # =========================

    total_pago = mensalidades_mes.filter(
        status="pago"
    ).aggregate(
        total=Coalesce(Sum("valor_final"), Decimal("0.00"), output_field=DecimalField())
    )["total"]

    total_pendente = mensalidades_mes.filter(
        status="pendente",
        vencimento__gte=hoje
    ).aggregate(
        total=Coalesce(Sum("valor_final"), Decimal("0.00"), output_field=DecimalField())
    )["total"]

    total_vencido = mensalidades_mes.filter(
        status="pendente",
        vencimento__lt=hoje
    ).aggregate(
        total=Coalesce(Sum("valor_final"), Decimal("0.00"), output_field=DecimalField())
    )["total"]

    # =========================
    # RECEITA (CAIXA REAL)
    # =========================

    receita_mes = Mensalidade.objects.filter(
        escola=escola,
        status="pago",
        pago_em__month=mes,
        pago_em__year=ano
    ).aggregate(
        total=Coalesce(Sum("valor_final"), Decimal("0.00"), output_field=DecimalField())
    )["total"]

    # =========================
    # INDICADORES AVANÇADOS
    # =========================

    total_mes = mensalidades_mes.aggregate(
        total=Coalesce(Sum("valor_final"), Decimal("0.00"), output_field=DecimalField())
    )["total"]

    inadimplencia = 0
    if total_mes > 0:
        inadimplencia = (total_vencido / total_mes) * 100

    previsao_receita = total_pendente + total_vencido

    quantidade_vencidas = mensalidades_mes.filter(
        status="pendente",
        vencimento__lt=hoje
    ).count()

    # =========================
    # PAGINAÇÃO
    # =========================

    paginator = Paginator(mensalidades_mes, 10)
    page = request.GET.get('page')
    mensalidades_paginadas = paginator.get_page(page)

    # =========================
    # 🔥 NOVO — MULTA AUTOMÁTICA
    # =========================

    def calcular_valor_atualizado(m):

        valor = m.valor_final

        if m.status == "pendente" and m.vencimento < hoje:

            multa = Decimal("30.00")

            dias_atraso = (hoje - m.vencimento).days

            # juros existe mas não entra (multiplicado por 0)
            juros = valor * Decimal("0.00033") * dias_atraso * Decimal("0")

            valor = valor + multa + juros

        return round(valor, 2)

    # aplica na lista paginada
    for m in mensalidades_paginadas:

        valor_original = m.valor_final
        multa = Decimal("0.00")
        dias_atraso = 0

    if m.status == "pendente" and m.vencimento < hoje:
        dias_atraso = (hoje - m.vencimento).days
        multa = Decimal("30.00")

    m.dias_atraso = dias_atraso
    m.multa_calculada = multa
    m.valor_atualizado = valor_original + multa

    # =========================
    # TURMAS
    # =========================

    turmas = Turma.objects.filter(escola=escola)

    # =========================
    # ANOS
    # =========================

    anos = list(range(2024, 2031))

    # =========================
    # CONTEXT
    # =========================

    context = {
        "mensalidades": mensalidades_paginadas,
        "today": hoje,

        # valores principais
        "total_pago": total_pago,
        "total_pendente": total_pendente,
        "total_vencido": total_vencido,
        "receita_mes": receita_mes,

        # inteligência
        "inadimplencia": round(inadimplencia, 2),
        "previsao_receita": previsao_receita,
        "quantidade_vencidas": quantidade_vencidas,

        # apoio
        "turmas": turmas,
        "mes_selecionado": mes,
        "mes_nome": mes_nome,
        "ano_selecionado": ano,
        "anos": anos,
        "meses_pt": meses_pt,
    }

    return render(
        request,
        "financeiro/listar_mensalidades.html",
        context
    )

# =========================
# EXPORTAR CSV (COM FILTRO)
# =========================

def exportar_csv(request):

    escola = request.escola


    mes = request.GET.get("mes")
    ano = request.GET.get("ano")

    mensalidades = Mensalidade.objects.filter(escola=escola)

    if mes and ano:
        mensalidades = mensalidades.filter(
            mes_referencia=int(mes),
            ano_referencia=int(ano)
        )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=mensalidades.csv'

    writer = csv.writer(response)
    writer.writerow(['Aluno', 'Mês', 'Ano', 'Valor', 'Status'])

    for m in mensalidades:
        writer.writerow([
            m.aluno.nome,
            m.mes_referencia,
            m.ano_referencia,
            m.valor_final,
            m.status
        ])

    return response


# =========================
# EXPORTAR EXCEL (COM FILTRO)
# =========================

def exportar_excel(request):

    escola = request.escola


    mes = request.GET.get("mes")
    ano = request.GET.get("ano")

    mensalidades = Mensalidade.objects.filter(escola=escola)

    if mes and ano:
        mensalidades = mensalidades.filter(
            mes_referencia=int(mes),
            ano_referencia=int(ano)
        )

    wb = Workbook()
    ws = wb.active

    ws.append(['Aluno', 'Mês', 'Ano', 'Valor', 'Status'])

    for m in mensalidades:
        ws.append([
            m.aluno.nome,
            m.mes_referencia,
            m.ano_referencia,
            float(m.valor_final),
            m.status
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    response['Content-Disposition'] = 'attachment; filename=mensalidades.xlsx'

    wb.save(response)

    return response


# =========================
# DAR BAIXA
# =========================

def dar_baixa_mensalidade(request, mensalidade_id):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:

        mensalidade = Mensalidade.objects.get(
            id=mensalidade_id,
            escola=request.escola

        )

        # 🔒 EVITA DUPLO PAGAMENTO
        if mensalidade.status == "pago":
            return JsonResponse({
                "success": False,
                "error": "Esta mensalidade já está marcada como paga."
            }, status=400)

        # 💰 DAR BAIXA
        mensalidade.status = "pago"
        mensalidade.pago_em = timezone.now()
        mensalidade.save()

        return JsonResponse({"success": True})

    except Mensalidade.DoesNotExist:

        return JsonResponse({
            "success": False,
            "error": "Mensalidade não encontrada"
        }, status=404)

    except Exception as e:

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


# =========================
# GERAR MENSALIDADES
# =========================

def gerar_mensalidades(request):

    escola = request.escola

    turmas = Turma.objects.filter(escola=escola)

    if request.method == "POST":

        turma_id = request.POST.get("turma_id")
        mes_inicio = int(request.POST.get("mes_inicio"))
        mes_fim = int(request.POST.get("mes_fim"))
        ano = int(request.POST.get("ano"))
        valor = Decimal(request.POST.get("valor"))
        dia_vencimento = int(request.POST.get("dia_vencimento"))

        # -------------------------------
        # Validações
        # -------------------------------

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

        # -------------------------------
        # Geração
        # -------------------------------

        for mes in range(mes_inicio, mes_fim + 1):

            ultimo_dia = calendar.monthrange(ano, mes)[1]

            for aluno in alunos:

                # 🔥 NOVO: usa vencimento do aluno ou padrão
                dia_aluno = aluno.dia_vencimento or dia_vencimento
                dia_final = min(dia_aluno, ultimo_dia)

                vencimento = date(ano, mes, dia_final)

                # desconto automático (ex: bolsa fixa)
                desconto_auto = aluno.desconto_mensal or Decimal("0.00")

                # garante tipo Decimal
                desconto_auto = Decimal(desconto_auto)

                # cálculo seguro
                valor_original = Decimal(valor)
                valor_final = valor_original - desconto_auto

                if valor_final < Decimal("0.00"):
                    valor_final = Decimal("0.00")

                mensalidade, created = Mensalidade.objects.get_or_create(

                    aluno=aluno,
                    mes_referencia=mes,
                    ano_referencia=ano,

                    defaults={
                        "escola": escola,

                        "valor_original": valor_original,
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


@require_POST
def estornar_mensalidade(request, id):

    mensalidade = Mensalidade.objects.get(id=id)

    mensalidade.status = "pendente"
    mensalidade.pago_em = None

    mensalidade.save()

    return JsonResponse({"success": True})


@login_required
def atualizar_desconto(request, id):

    if request.method == "POST":

        dados = json.loads(request.body)

        desconto = Decimal(dados.get("desconto", "0"))

        m = Mensalidade.objects.get(id=id, escola=request.escola
)

        m.desconto = desconto
        m.valor_final = m.valor_original - desconto

        if m.valor_final < 0:
            m.valor_final = Decimal("0.00")

        m.save()

        return JsonResponse({
            "success": True,
            "valor_formatado": f"R$ {m.valor_final:.2f}".replace(".", ",")
        })