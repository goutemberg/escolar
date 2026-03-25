from django.http import HttpResponse
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from financeiro.models import Mensalidade
from django.utils.timezone import localtime


def gerar_recibo(request, mensalidade_id):

    mensalidade = Mensalidade.objects.select_related('aluno').get(id=mensalidade_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="recibo_{mensalidade.id}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # =========================
    # ESTILOS CUSTOM
    # =========================

    title_style = ParagraphStyle(
        'Titulo',
        parent=styles['Title'],
        alignment=1
    )

    section_style = ParagraphStyle(
        'Secao',
        parent=styles['Heading3'],
        spaceAfter=10
    )

    normal_style = styles['Normal']

    destaque_style = ParagraphStyle(
        'Destaque',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.green,
        spaceAfter=10
    )

    elements = []

    escola = request.escola


    # =========================
    # FORMATAÇÕES
    # =========================

    valor_original = f"{mensalidade.valor_original:.2f}"
    desconto = f"{mensalidade.desconto:.2f}"
    valor_final = f"{mensalidade.valor_final:.2f}"

    data_pagamento = (
    localtime(mensalidade.pago_em).strftime("%d/%m/%Y %H:%M")
    if mensalidade.pago_em
    else "Não informado"
)

    forma_pagamento = getattr(mensalidade, "forma_pagamento", "Não informado")

    # =========================
    # CABEÇALHO
    # =========================

    elements.append(Paragraph(f"<b>{escola.nome}</b>", title_style))
    elements.append(Spacer(1, 5))

    elements.append(Paragraph("RECIBO DE PAGAMENTO", section_style))
    elements.append(Spacer(1, 15))

    # =========================
    # DADOS DO ALUNO
    # =========================

    elements.append(Paragraph("<b>DADOS DO ALUNO</b>", section_style))

    tabela_aluno = Table([
        ["Aluno:", mensalidade.aluno.nome],
        ["Turma:", mensalidade.aluno.turma.nome],
    ], colWidths=[4*cm, 10*cm])

    tabela_aluno.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(tabela_aluno)
    elements.append(Spacer(1, 20))

    # =========================
    # PAGAMENTO
    # =========================

    elements.append(Paragraph("<b>DADOS DO PAGAMENTO</b>", section_style))

    tabela_pagamento = [
        ["Valor original:", f"R$ {valor_original}"]
    ]

    # 👉 Só mostra desconto se existir
    if mensalidade.desconto and mensalidade.desconto > 0:
        tabela_pagamento.append(["Desconto:", f"- R$ {desconto}"])

    tabela_pagamento += [
        ["Valor pago:", f"R$ {valor_final}"],
        ["Data:", data_pagamento],
        ["Forma:", forma_pagamento],
    ]

    tabela_pagamento = Table(tabela_pagamento, colWidths=[4*cm, 10*cm])

    tabela_pagamento.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(tabela_pagamento)
    elements.append(Spacer(1, 20))

    # =========================
    # DESTAQUE VALOR
    # =========================

    box_valor = Table([
        [f"VALOR RECEBIDO: R$ {valor_final}"]
    ], colWidths=[14*cm])

    box_valor.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgreen),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))

    elements.append(box_valor)
    elements.append(Spacer(1, 25))

    # =========================
    # TEXTO
    # =========================

    elements.append(Paragraph(
        "Declaramos que recebemos o valor acima referente à mensalidade escolar.",
        normal_style
    ))

    elements.append(Spacer(1, 50))

    # =========================
    # ASSINATURA
    # =========================

    elements.append(Paragraph("__________________________________", normal_style))
    elements.append(Paragraph("Assinatura / Carimbo", normal_style))

    # =========================
    # BUILD
    # =========================

    doc.build(elements)

    return response