from datetime import date
from calendar import monthrange

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from django.shortcuts import render, get_object_or_404

from home.models import Presenca, Turma, Docente, Aluno
from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Font, Alignment

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from io import BytesIO
import matplotlib.pyplot as plt
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors


@login_required
def presenca_aluno_mensal(request):

    user = request.user
    escola = user.escola

    # =====================================
    # CONTROLE DE ACESSO
    # =====================================
    professor = None

    if user.role == "professor":
        professor = Docente.objects.filter(
            user=user,
            escola=escola,
        ).first()

        if not professor:
            return render(request, "errors/403.html", status=403)

    elif user.role not in ("diretor", "coordenador"):
        return render(request, "errors/403.html", status=403)

    hoje = date.today()

    # =====================================
    # FILTROS
    # =====================================
    ano = int(request.GET.get("ano", hoje.year))
    mes = request.GET.get("mes")
    turma_id = request.GET.get("turma")

    # =====================================
    # PERÍODO
    # =====================================
    if mes:
        mes = int(mes)
        _, ultimo_dia = monthrange(ano, mes)
        data_inicio = date(ano, mes, 1)
        data_fim = date(ano, mes, ultimo_dia)
        tipo_relatorio = "mensal"
        mes_atual = mes
    else:
        data_inicio = date(ano, 1, 1)
        data_fim = date(ano, 12, 31)
        tipo_relatorio = "anual"
        mes_atual = None

    # =====================================
    # BASE DE PRESENÇAS
    # =====================================
    presencas = Presenca.objects.filter(
        chamada__data__range=(data_inicio, data_fim),
        aluno__escola=escola,
    )

    # Apenas professores enxergam suas próprias chamadas
    if user.role == "professor":
        presencas = presencas.filter(chamada__professor=professor)

    if turma_id and turma_id != "None":
        presencas = presencas.filter(chamada__turma_id=turma_id)

    # =====================================
    # AGRUPAMENTO
    # =====================================
    resumo = list(
        presencas.values(
            "aluno_id",
            "aluno__nome",
            "aluno__turma_principal__nome",
        )
        .annotate(
            total_aulas=Count("id"),
            total_presentes=Count(
                "id",
                filter=Q(presente=True),
            ),
            total_ausentes=Count(
                "id",
                filter=Q(presente=False),
            ),
        )
        .annotate(percentual_presenca=F("total_presentes") * 100.0 / F("total_aulas"))
        .order_by("aluno__nome")
    )

    # =====================================
    # AJUSTES
    # =====================================
    for r in resumo:
        if r["total_aulas"] == 0:
            r["percentual_presenca"] = 0
        else:
            r["percentual_presenca"] = round(
                r["percentual_presenca"],
                1,
            )

    # =====================================
    # DASHBOARD
    # =====================================
    total_alunos = len(resumo)

    total_aulas = sum(r["total_aulas"] for r in resumo)

    media_presenca = (
        round(
            sum(r["percentual_presenca"] for r in resumo) / total_alunos,
            1,
        )
        if total_alunos
        else 0
    )

    alunos_risco = sum(1 for r in resumo if r["percentual_presenca"] < 75)

    # =====================================
    # DADOS AUXILIARES
    # =====================================
    turmas = Turma.objects.filter(escola=escola).order_by("nome")

    meses = [
        {"valor": 1, "nome": "Janeiro"},
        {"valor": 2, "nome": "Fevereiro"},
        {"valor": 3, "nome": "Março"},
        {"valor": 4, "nome": "Abril"},
        {"valor": 5, "nome": "Maio"},
        {"valor": 6, "nome": "Junho"},
        {"valor": 7, "nome": "Julho"},
        {"valor": 8, "nome": "Agosto"},
        {"valor": 9, "nome": "Setembro"},
        {"valor": 10, "nome": "Outubro"},
        {"valor": 11, "nome": "Novembro"},
        {"valor": 12, "nome": "Dezembro"},
    ]

    return render(
        request,
        "pages/relatorios/presenca_aluno_mensal.html",
        {
            "resumo": resumo,
            "turmas": turmas,
            "meses": meses,
            "mes_atual": mes_atual,
            "ano_atual": ano,
            "turma_selecionada": turma_id,
            "tipo_relatorio": tipo_relatorio,
            "total_alunos": total_alunos,
            "total_aulas": total_aulas,
            "media_presenca": media_presenca,
            "alunos_risco": alunos_risco,
        },
    )


@login_required
def export_presenca_aluno_mensal_excel(request):
    """
    Exporta para Excel o relatório de presença por aluno
    - Mensal (quando mês é informado)
    - Anual (quando mês NÃO é informado)
    """

    user = request.user

    # ============================
    # CONTROLE DE ACESSO
    # ============================
    professor = Docente.objects.filter(user=user).first()

    if not professor and user.role not in ("diretor", "coordenador"):
        return render(request, "errors/403.html", status=403)

    hoje = date.today()

    # ============================
    # FILTROS
    # ============================
    ano = int(request.GET.get("ano", hoje.year))
    mes = request.GET.get("mes")  # pode ser None
    turma_id = request.GET.get("turma")

    # ============================
    # PERÍODO (MENSAL OU ANUAL)
    # ============================
    if mes:
        mes = int(mes)
        _, ultimo_dia = monthrange(ano, mes)
        data_inicio = date(ano, mes, 1)
        data_fim = date(ano, mes, ultimo_dia)
        tipo_relatorio = "mensal"
    else:
        data_inicio = date(ano, 1, 1)
        data_fim = date(ano, 12, 31)
        tipo_relatorio = "anual"

    # ============================
    # QUERY BASE
    # ============================
    presencas = Presenca.objects.filter(
        chamada__diario__data_ministrada__range=(data_inicio, data_fim),
        aluno__escola=user.escola,
    )

    if professor:
        presencas = presencas.filter(chamada__diario__professor=professor)

    if turma_id:
        presencas = presencas.filter(chamada__diario__turma_id=turma_id)

    resumo = (
        presencas.values(
            "aluno__nome",
            "aluno__turma_principal__nome",
        )
        .annotate(
            total_aulas=Count("id"),
            total_presentes=Count("id", filter=Q(presente=True)),
            total_ausentes=Count("id", filter=Q(presente=False)),
        )
        .annotate(percentual_presenca=(F("total_presentes") * 100.0 / F("total_aulas")))
        .order_by("aluno__nome")
    )

    # ============================
    # CRIA EXCEL
    # ============================
    wb = openpyxl.Workbook()
    ws = wb.active

    if tipo_relatorio == "mensal":
        ws.title = "Presença Mensal"
    else:
        ws.title = "Presença Anual"

    # HEADER
    headers = [
        "Aluno",
        "Turma",
        "Total de Aulas",
        "Presenças",
        "Faltas",
        "Presença (%)",
    ]

    ws.append(headers)

    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    # DADOS
    for r in resumo:
        ws.append(
            [
                r["aluno__nome"],
                r["aluno__turma_principal__nome"] or "-",
                r["total_aulas"],
                r["total_presentes"],
                r["total_ausentes"],
                round(r["percentual_presenca"], 1),
            ]
        )

    # AUTO WIDTH
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = length + 2

    # ============================
    # RESPONSE
    # ============================
    if tipo_relatorio == "mensal":
        filename = f"presenca_alunos_{mes:02d}_{ano}.xlsx"
    else:
        filename = f"presenca_alunos_anual_{ano}.xlsx"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response


@login_required
def pdf_presenca_aluno_mensal(request):
    """
    PDF de presença por aluno
    - Mensal (quando mês é informado)
    - Anual (quando mês NÃO é informado)
    """

    user = request.user
    escola = user.escola
    professor = Docente.objects.filter(user=user).first()

    if not professor and user.role not in ("diretor", "coordenador"):
        return render(request, "errors/403.html", status=403)

    hoje = date.today()

    # ============================
    # FILTROS
    # ============================
    ano = int(request.GET.get("ano", hoje.year))
    mes = request.GET.get("mes")
    turma_id = request.GET.get("turma")

    # ============================
    # PERÍODO
    # ============================
    if mes:
        mes = int(mes)
        _, ultimo_dia = monthrange(ano, mes)
        data_inicio = date(ano, mes, 1)
        data_fim = date(ano, mes, ultimo_dia)
        titulo = "Relatório de Presença Mensal"
        periodo_label = f"{mes:02d}/{ano}"
        filename = f"presenca_alunos_{mes:02d}_{ano}.pdf"
    else:
        data_inicio = date(ano, 1, 1)
        data_fim = date(ano, 12, 31)
        titulo = "Relatório de Presença Anual"
        periodo_label = f"Ano {ano}"
        filename = f"presenca_alunos_anual_{ano}.pdf"

    # ============================
    # QUERY
    # ============================
    presencas = Presenca.objects.filter(
        chamada__diario__data_ministrada__range=(data_inicio, data_fim),
        aluno__escola=escola,
    )

    if professor:
        presencas = presencas.filter(chamada__diario__professor=professor)

    if turma_id and turma_id != "None":
        presencas = presencas.filter(chamada__diario__turma_id=turma_id)

    resumo = (
        presencas.values(
            "aluno__nome",
            "aluno__turma_principal__nome",
        )
        .annotate(
            total_aulas=Count("id"),
            presentes=Count("id", filter=Q(presente=True)),
            faltas=Count("id", filter=Q(presente=False)),
        )
        .annotate(percentual=F("presentes") * 100.0 / F("total_aulas"))
        .order_by("aluno__nome")
    )

    # ============================
    # PDF
    # ============================
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    pdf = canvas.Canvas(response, pagesize=A4)
    largura, altura = A4

    # ============================
    # BARRA SUPERIOR
    # ============================
    pdf.setFillColorRGB(0.98, 0.73, 0.51)  # #fab982
    pdf.rect(0, altura - 2.5 * cm, largura, 2.5 * cm, fill=1)

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, altura - 1.5 * cm, escola.nome)

    # ============================
    # DADOS ESCOLA
    # ============================
    pdf.setFont("Helvetica", 10)

    endereco_formatado = f"{escola.endereco}, {escola.numero} - {escola.bairro}"

    pdf.drawString(2 * cm, altura - 3.2 * cm, f"CNPJ: {escola.cnpj}")
    pdf.drawString(2 * cm, altura - 3.8 * cm, f"Endereço: {endereco_formatado}")
    pdf.drawString(
        2 * cm,
        altura - 4.4 * cm,
        f"{escola.cidade} - {escola.estado} | CEP: {escola.cep}",
    )
    pdf.drawString(
        2 * cm,
        altura - 5.0 * cm,
        f"Telefone: {escola.telefone} | Email: {escola.email}",
    )

    pdf.line(2 * cm, altura - 5.6 * cm, largura - 2 * cm, altura - 5.6 * cm)

    # ============================
    # TÍTULO
    # ============================
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(2 * cm, altura - 6.6 * cm, titulo)

    pdf.setFont("Helvetica", 11)
    pdf.drawString(2 * cm, altura - 7.2 * cm, f"Período: {periodo_label}")

    # ============================
    # CABEÇALHO TABELA
    # ============================
    y = altura - 8.5 * cm

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(2 * cm, y, "Aluno")
    pdf.drawString(8 * cm, y, "Turma")
    pdf.drawRightString(12 * cm, y, "Aulas")
    pdf.drawRightString(14 * cm, y, "Pres.")
    pdf.drawRightString(16 * cm, y, "Falt.")
    pdf.drawRightString(18.5 * cm, y, "%")

    pdf.line(2 * cm, y - 0.2 * cm, largura - 2 * cm, y - 0.2 * cm)

    y -= 0.8 * cm
    pdf.setFont("Helvetica", 10)

    # ============================
    # LINHAS
    # ============================
    for r in resumo:

        percentual = round(r["percentual"], 1)

        # Cor do percentual
        if percentual >= 75:
            pdf.setFillColorRGB(0.16, 0.62, 0.35)
        elif percentual >= 60:
            pdf.setFillColorRGB(1, 0.6, 0)
        else:
            pdf.setFillColorRGB(0.8, 0.2, 0.2)

        pdf.drawString(2 * cm, y, r["aluno__nome"][:28])
        pdf.drawString(8 * cm, y, (r["aluno__turma_principal__nome"] or "-")[:12])

        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawRightString(12 * cm, y, str(r["total_aulas"]))
        pdf.drawRightString(14 * cm, y, str(r["presentes"]))
        pdf.drawRightString(16 * cm, y, str(r["faltas"]))

        # Percentual colorido
        if percentual >= 75:
            pdf.setFillColorRGB(0.16, 0.62, 0.35)
        elif percentual >= 60:
            pdf.setFillColorRGB(1, 0.6, 0)
        else:
            pdf.setFillColorRGB(0.8, 0.2, 0.2)

        pdf.drawRightString(18.5 * cm, y, f"{percentual}%")

        pdf.setFillColorRGB(0, 0, 0)

        y -= 0.6 * cm

        if y < 2 * cm:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = altura - 2 * cm

    # ============================
    # RODAPÉ
    # ============================
    pdf.setFont("Helvetica", 8)
    pdf.drawString(
        2 * cm, 1.5 * cm, f"Documento emitido em {date.today().strftime('%d/%m/%Y')}"
    )

    pdf.showPage()
    pdf.save()

    return response


@login_required
def pdf_presenca_aluno_individual(request, aluno_id):
    user = request.user
    escola = user.escola

    professor = Docente.objects.filter(user=user).first()

    if not professor and user.role not in ("diretor", "coordenador"):
        return render(request, "errors/403.html", status=403)

    hoje = date.today()

    mes = request.GET.get("mes")
    ano = int(request.GET.get("ano", hoje.year))
    turma_id = request.GET.get("turma")

    # ==========================================
    # PERÍODO
    # ==========================================

    if mes:
        mes = int(mes)
        _, ultimo_dia = monthrange(ano, mes)

        data_inicio = date(ano, mes, 1)
        data_fim = date(ano, mes, ultimo_dia)

        titulo_periodo = f"{mes:02d}/{ano}"

    else:
        data_inicio = date(ano, 1, 1)
        data_fim = date(ano, 12, 31)

        titulo_periodo = f"Ano {ano}"

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=escola,
    )

    # ==========================================
    # PRESENÇAS
    # ==========================================

    presencas = Presenca.objects.filter(
        aluno=aluno,
        chamada__data__range=(data_inicio, data_fim),
    )

    if user.role == "professor":
        presencas = presencas.filter(chamada__professor=professor)

    if turma_id and turma_id != "None":
        presencas = presencas.filter(chamada__turma_id=turma_id)

    total_aulas = presencas.count()
    presentes = presencas.filter(presente=True).count()

    faltas = presencas.filter(presente=False).count()

    percentual = presentes * 100 / total_aulas if total_aulas else 0

    # ==========================================
    # STATUS
    # ==========================================

    if percentual >= 75:
        status = "Frequência Regular"
        status_color = (0.16, 0.62, 0.35)

    elif percentual >= 60:
        status = "Atenção"
        status_color = (1, 0.60, 0)

    else:
        status = "Risco de Reprovação"
        status_color = (0.80, 0.20, 0.20)

    # ==========================================
    # GRÁFICO
    # ==========================================

    fig, ax = plt.subplots(figsize=(5.3, 5.3))

    if total_aulas == 0:

        ax.pie(
            [1],
            colors=["#d9d9d9"],
            startangle=90,
            wedgeprops=dict(
                width=0.4,
                edgecolor="white",
            ),
        )

        ax.text(
            0,
            0,
            "Sem\nDados",
            ha="center",
            va="center",
            fontsize=15,
            fontweight="bold",
        )

    else:

        ax.pie(
            [presentes, faltas],
            colors=[
                "#2ecc71",
                "#e74c3c",
            ],
            startangle=90,
            autopct=None,
            wedgeprops=dict(
                width=0.32,
                edgecolor="white",
                linewidth=2,
            ),
        )

        ax.text(
            0,
            0,
            f"{round(percentual, 1)}%",
            ha="center",
            va="center",
            fontsize=22,
            fontweight="bold",
            color="#111827",
        )

    plt.tight_layout()

    img_buffer = BytesIO()

    plt.savefig(
        img_buffer,
        format="png",
        transparent=True,
    )

    plt.close(fig)

    img_buffer.seek(0)

    # ==========================================
    # PDF
    # ==========================================

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        f'inline; filename="frequencia_{aluno.nome.replace(" ", "_")}.pdf"'
    )

    pdf = canvas.Canvas(
        response,
        pagesize=A4,
    )

    largura, altura = A4

    # ==========================================
    # CORES
    # ==========================================

    azul = colors.HexColor("#2563EB")
    cinza = colors.HexColor("#6B7280")
    cinza_claro = colors.HexColor("#E5E7EB")

    # ==========================================
    # CABEÇALHO
    # ==========================================

    pdf.setFillColor(azul)

    pdf.rect(
        0,
        altura - 2.2 * cm,
        largura,
        2.2 * cm,
        stroke=0,
        fill=1,
    )

    pdf.setFillColor(colors.white)

    pdf.setFont(
        "Helvetica-Bold",
        22,
    )

    pdf.drawString(
        2 * cm,
        altura - 1.4 * cm,
        escola.nome.upper(),
    )

    pdf.setFillColor(colors.black)

    pdf.setFont(
        "Helvetica-Bold",
        20,
    )

    pdf.drawString(
        2 * cm,
        altura - 3.3 * cm,
        "RELATÓRIO INDIVIDUAL DE FREQUÊNCIA",
    )

    pdf.setStrokeColor(cinza_claro)

    pdf.line(
        2 * cm,
        altura - 3.6 * cm,
        largura - 2 * cm,
        altura - 3.6 * cm,
    )

    # ==========================================
    # DADOS DA ESCOLA
    # ==========================================

    pdf.setFillColor(cinza)

    pdf.setFont(
        "Helvetica",
        9,
    )

    endereco = (
        f"{escola.endereco}, {escola.numero} - "
        f"{escola.bairro} - "
        f"{escola.cidade}/{escola.estado}"
    )

    pdf.drawString(
        2 * cm,
        altura - 4.2 * cm,
        f"CNPJ: {escola.cnpj}",
    )

    pdf.drawString(
        8.5 * cm,
        altura - 4.2 * cm,
        f"Telefone: {escola.telefone}",
    )

    pdf.drawString(
        2 * cm,
        altura - 4.8 * cm,
        endereco,
    )

    pdf.drawString(
        2 * cm,
        altura - 5.4 * cm,
        escola.email or "",
    )

    # ==========================================
    # DADOS DO ALUNO
    # ==========================================

    y = altura - 6.8 * cm

    pdf.setFillColor(colors.black)

    pdf.setFont(
        "Helvetica-Bold",
        16,
    )

    pdf.drawString(
        2 * cm,
        y,
        aluno.nome,
    )

    pdf.setFont(
        "Helvetica",
        10,
    )

    pdf.setFillColor(cinza)

    pdf.drawString(
        2 * cm,
        y - 0.6 * cm,
        f"Turma: {aluno.turma_principal.nome if aluno.turma_principal else '-'}",
    )

    pdf.drawString(
        9 * cm,
        y - 0.6 * cm,
        f"Período: {titulo_periodo}",
    )

    # ==========================================
    # CARDS
    # ==========================================

    card_y = altura - 10.5 * cm

    card_w = 3.3 * cm
    card_h = 2.6 * cm
    espaco = 0.35 * cm

    cards = [
        ("Aulas", total_aulas, "#2563EB"),
        ("Presentes", presentes, "#22C55E"),
        ("Faltas", faltas, "#EF4444"),
        ("Frequência", f"{round(percentual, 1)}%", "#F59E0B"),
    ]

    for i, (titulo, valor, cor) in enumerate(cards):
        x = 2 * cm + (card_w + espaco) * i

        pdf.setFillColor(colors.white)

        pdf.roundRect(
            x,
            card_y,
            card_w,
            card_h,
            8,
            stroke=1,
            fill=1,
        )

        pdf.setStrokeColor(colors.HexColor("#DDDDDD"))

        pdf.roundRect(
            x,
            card_y,
            card_w,
            card_h,
            8,
            stroke=1,
            fill=0,
        )

        pdf.setFillColor(colors.HexColor(cor))

        pdf.setFont(
            "Helvetica-Bold",
            16,
        )

        pdf.drawCentredString(
            x + card_w / 2,
            card_y + 1.45 * cm,
            str(valor),
        )

        pdf.setFillColor(cinza)

        pdf.setFont(
            "Helvetica",
            9,
        )

        pdf.drawCentredString(
            x + card_w / 2,
            card_y + 0.55 * cm,
            titulo,
        )

        # ==========================================
    # STATUS
    # ==========================================

    status_y = card_y - 2.9 * cm

    pdf.setFillColor(colors.HexColor("#F8FAFC"))

    pdf.roundRect(
        2 * cm,
        status_y,
        8.5 * cm,
        2.2 * cm,
        8,
        stroke=0,
        fill=1,
    )

    pdf.setFillColor(cinza)

    pdf.setFont(
        "Helvetica-Bold",
        10,
    )

    pdf.drawString(
        3.4 * cm,
        status_y + 1.5 * cm,
        "SITUAÇÃO DO ALUNO",
    )

    pdf.setFillColorRGB(*status_color)

    pdf.setFont(
        "Helvetica-Bold",
        14,
    )

    pdf.drawString(
        2.0 * cm,
        status_y + 0.5 * cm,
        status.upper(),
    )

    # ==========================================
    # GRÁFICO
    # ==========================================

    pdf.setFont(
        "Helvetica-Bold",
        12,
    )

    image = ImageReader(img_buffer)

    pdf.setFillColor(colors.black)

    pdf.drawImage(
        image,
        11.2 * cm,
        altura - 18.8 * cm,
        width=8.4 * cm,
        height=8.4 * cm,
        mask="auto",
    )

    resumo_y = 4.2 * cm

    pdf.setFillColor(colors.black)

    pdf.setFont(
        "Helvetica-Bold",
        11,
    )

    pdf.drawString(2 * cm, resumo_y + 1.2 * cm, "Resumo")

    pdf.setFont(
        "Helvetica",
        9,
    )

    texto = (
        f"No período analisado o aluno participou de "
        f"{total_aulas} aulas, registrando presença em "
        f"{presentes} delas, alcançando frequência de "
        f"{round(percentual,1)}%."
    )

    pdf.drawString(
        2 * cm,
        resumo_y + 0.5 * cm,
        texto,
    )

    # ==========================================
    # RODAPÉ
    # ==========================================

    pdf.setStrokeColor(cinza_claro)

    pdf.line(
        2 * cm,
        2.3 * cm,
        largura - 2 * cm,
        2.3 * cm,
    )

    pdf.setFillColor(cinza)

    pdf.setFont(
        "Helvetica",
        8,
    )

    pdf.drawString(
        2 * cm,
        1.7 * cm,
        f"Documento emitido automaticamente em {date.today().strftime('%d/%m/%Y')}",
    )

    pdf.drawRightString(
        largura - 2 * cm,
        1.7 * cm,
        escola.nome,
    )

    # Finaliza a página
    pdf.showPage()

    # Grava o PDF
    pdf.save()

    return response
