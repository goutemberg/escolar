from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator

from home.models import Chamada, Docente, Turma

from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape


from django.db.models import Q


def buscar_chamadas_relatorio(request):

    escola = request.user.escola

    chamadas = (
        Chamada.objects.select_related(
            "criado_por",
            "turma",
            "professor",
            "professor__user",
            "diario",
        )
        .filter(escola=escola)
        .order_by("-criado_em")
    )

    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")
    professor_id = request.GET.get("professor")
    turma_id = request.GET.get("turma")

    busca = request.GET.get("busca")
    situacao = request.GET.get("situacao")

    # ===========================
    # FILTROS
    # ===========================

    if data_inicio:
        chamadas = chamadas.filter(data__gte=data_inicio)

    if data_fim:
        chamadas = chamadas.filter(data__lte=data_fim)

    if professor_id:
        chamadas = chamadas.filter(professor_id=professor_id)

    if turma_id:
        chamadas = chamadas.filter(turma_id=turma_id)

    if busca:
        chamadas = chamadas.filter(
            Q(professor__nome__icontains=busca)
            | Q(turma__nome__icontains=busca)
            | Q(criado_por__first_name__icontains=busca)
            | Q(criado_por__last_name__icontains=busca)
            | Q(criado_por__username__icontains=busca)
        )

    chamadas_lista = list(chamadas)

    # ===========================
    # SITUAÇÃO
    # ===========================

    if situacao in ["professor", "terceiro"]:

        resultado = []

        for chamada in chamadas_lista:

            professor_user_id = None

            if chamada.professor and chamada.professor.user:
                professor_user_id = chamada.professor.user.id

            foi_professor = professor_user_id == chamada.criado_por_id

            if situacao == "professor" and foi_professor:
                resultado.append(chamada)

            elif situacao == "terceiro" and not foi_professor:
                resultado.append(chamada)

        chamadas_lista = resultado

    # ===========================
    # INDICADORES
    # ===========================

    total_chamadas = len(chamadas_lista)

    chamadas_professor = 0
    chamadas_terceiros = 0

    for chamada in chamadas_lista:

        professor_user_id = None

        if chamada.professor and chamada.professor.user:
            professor_user_id = chamada.professor.user.id

        if professor_user_id == chamada.criado_por_id:
            chamadas_professor += 1
        else:
            chamadas_terceiros += 1

    return {
        "chamadas": chamadas_lista,
        "total_chamadas": total_chamadas,
        "chamadas_professor": chamadas_professor,
        "chamadas_terceiros": chamadas_terceiros,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "professor_id": professor_id,
        "turma_id": turma_id,
        "busca": busca,
        "situacao": situacao,
    }


@login_required
def relatorio_chamada_professor(request):

    dados = buscar_chamadas_relatorio(request)

    page_size = request.GET.get("page_size", 25)

    try:
        page_size = int(page_size)
    except (ValueError, TypeError):
        page_size = 25

    paginator = Paginator(dados["chamadas"], page_size)

    page_number = request.GET.get("page", 1)

    chamadas = paginator.get_page(page_number)

    professores = Docente.objects.filter(
        ativo=True,
        escola=request.user.escola,
    ).order_by("nome")

    turmas = Turma.objects.filter(escola=request.user.escola).order_by("nome")

    query_params = request.GET.copy()

    if "page" in query_params:
        query_params.pop("page")

    query_string = query_params.urlencode()

    contexto = {
        "chamadas": chamadas,
        "professores": professores,
        "turmas": turmas,
        "total_chamadas": dados["total_chamadas"],
        "chamadas_professor": dados["chamadas_professor"],
        "chamadas_terceiros": dados["chamadas_terceiros"],
        "total_professores": professores.count(),
        "data_inicio": dados["data_inicio"],
        "data_fim": dados["data_fim"],
        "professor_selecionado": dados["professor_id"],
        "turma_selecionada": dados["turma_id"],
        "busca": dados["busca"],
        "situacao_selecionada": dados["situacao"],
        "page_size": page_size,
        "query_string": query_string,
    }

    return render(
        request,
        "pages/chamada/relatorio_chamada_professor.html",
        contexto,
    )


@login_required
def relatorio_chamada_professor_pdf(request):

    dados = buscar_chamadas_relatorio(request)

    chamadas = dados["chamadas"]

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=25,
        bottomMargin=20,
    )

    elements = []

    styles = getSampleStyleSheet()

    AZUL_NUCLEO = colors.HexColor("#1E88E5")

    escola = request.user.escola

    # ==========================================
    # CABEÇALHO
    # ==========================================

    elements.append(
        Paragraph(
            "<b>RELATÓRIO DE CHAMADAS DOS PROFESSORES</b>",
            styles["Title"],
        )
    )

    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            f"<b>Escola:</b> {escola.nome}",
            styles["Normal"],
        )
    )

    elements.append(
        Paragraph(
            f"<b>Emitido por:</b> {request.user.get_full_name() or request.user.username}",
            styles["Normal"],
        )
    )

    elements.append(
        Paragraph(
            f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 12))

    # ==========================================
    # FILTROS
    # ==========================================

    filtros = []

    if dados["busca"]:
        filtros.append(f"Busca: {dados['busca']}")

    if dados["professor_id"]:
        professor = (
            Docente.objects.filter(id=dados["professor_id"]).only("nome").first()
        )

        if professor:
            filtros.append(f"Professor: {professor.nome}")

    if dados["turma_id"]:
        turma = Turma.objects.filter(id=dados["turma_id"]).only("nome").first()

        if turma:
            filtros.append(f"Turma: {turma.nome}")

    if dados["situacao"]:
        filtros.append(f"Situação: {dados['situacao'].title()}")

    if dados["data_inicio"] or dados["data_fim"]:

        periodo = f"{dados['data_inicio'] or '--'} até {dados['data_fim'] or '--'}"

        filtros.append(f"Período: {periodo}")

    if filtros:

        elements.append(
            Paragraph(
                "<b>Filtros aplicados</b>",
                styles["Heading2"],
            )
        )

        for filtro in filtros:
            elements.append(Paragraph(f"• {filtro}", styles["Normal"]))

        elements.append(Spacer(1, 12))

    # ==========================================
    # RESUMO
    # ==========================================

    resumo = [
        ["Indicador", "Quantidade"],
        ["Total de Chamadas", str(dados["total_chamadas"])],
        ["Pelo Professor", str(dados["chamadas_professor"])],
        ["Por Terceiros", str(dados["chamadas_terceiros"])],
    ]

    tabela_resumo = Table(
        resumo,
        colWidths=[220, 120],
    )

    tabela_resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), AZUL_NUCLEO),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ]
        )
    )

    elements.append(tabela_resumo)

    elements.append(Spacer(1, 18))

    # ==========================================
    # TABELA
    # ==========================================

    tabela = [
        [
            Paragraph("<b>Data</b>", styles["BodyText"]),
            Paragraph("<b>Turma</b>", styles["BodyText"]),
            Paragraph("<b>Professor</b>", styles["BodyText"]),
            Paragraph("<b>Lançado por</b>", styles["BodyText"]),
            Paragraph("<b>Situação</b>", styles["BodyText"]),
        ]
    ]

    for chamada in chamadas:

        if (
            chamada.professor
            and chamada.professor.user
            and chamada.professor.user.id == chamada.criado_por_id
        ):
            situacao = "Professor"
        else:
            situacao = "Terceiro"

        tabela.append(
            [
                Paragraph(
                    chamada.data.strftime("%d/%m/%Y"),
                    styles["BodyText"],
                ),
                Paragraph(
                    chamada.turma.nome if chamada.turma else "-",
                    styles["BodyText"],
                ),
                Paragraph(
                    chamada.professor.nome if chamada.professor else "-",
                    styles["BodyText"],
                ),
                Paragraph(
                    (
                        (
                            chamada.criado_por.get_full_name()
                            or chamada.criado_por.username
                        )
                        if chamada.criado_por
                        else "-"
                    ),
                    styles["BodyText"],
                ),
                Paragraph(
                    situacao,
                    styles["BodyText"],
                ),
            ]
        )

    tabela_pdf = Table(
        tabela,
        repeatRows=1,
        colWidths=[
            65,
            190,
            180,
            200,
            70,
        ],
    )

    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_NUCLEO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("GRID", (0, 0), (-1, -1), 0.30, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    for linha in range(1, len(tabela)):
        if linha % 2 == 0:
            estilo.append(
                (
                    "BACKGROUND",
                    (0, linha),
                    (-1, linha),
                    colors.HexColor("#F5F7FA"),
                )
            )

    tabela_pdf.setStyle(TableStyle(estilo))

    elements.append(tabela_pdf)

    doc.build(elements)

    pdf = buffer.getvalue()

    buffer.close()

    return HttpResponse(
        pdf,
        content_type="application/pdf",
    )
