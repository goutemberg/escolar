from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from home.models import Aluno, Avaliacao, Disciplina, Nota, Presenca, Turma, Chamada
from home.utils import arredondar_media_personalizada
from django.contrib.auth.decorators import login_required


# =========================================
# PDF DO BOLETIM
# =========================================

@login_required
def gerar_pdf_boletim(request, aluno_id):

    aluno = get_object_or_404(Aluno, id=aluno_id)
    escola = aluno.escola
    turma = aluno.turma_principal

    disciplinas = Disciplina.objects.filter(
        turmadisciplina__turma=turma,
        escola=escola
    ).distinct()

    avaliacoes = Avaliacao.objects.filter(
        turma=turma,
        escola=escola
    ).select_related("disciplina", "tipo")

    notas = Nota.objects.filter(
        aluno=aluno,
        avaliacao__in=avaliacoes
    ).select_related("avaliacao")

    # 🔥 AGORA COM DETALHE DAS NOTAS
    notas_por_disciplina = defaultdict(lambda: defaultdict(list))

    for nota in notas:
        disciplina_id = nota.avaliacao.disciplina_id
        bimestre = nota.avaliacao.bimestre
        peso = nota.avaliacao.tipo.peso if nota.avaliacao.tipo else 1

        if nota.valor is not None:
            notas_por_disciplina[disciplina_id][bimestre].append({
                "valor": float(nota.valor),
                "peso": float(peso),
                "tipo": nota.avaliacao.tipo.nome if nota.avaliacao.tipo else "Avaliação"
            })

    # FALTAS
    faltas_por_disciplina = defaultdict(int)

    chamadas = Chamada.objects.filter(diario__turma=turma)

    presencas = Presenca.objects.filter(
        aluno=aluno,
        chamada__in=chamadas
    ).select_related("chamada__diario")

    for p in presencas:
        if not p.presente:
            faltas_por_disciplina[p.chamada.diario.disciplina_id] += 1

    # 🔥 MONTA ESTRUTURA FINAL
    boletim = []

    for disciplina in disciplinas:

        bimestres = {}
        notas_detalhadas = {}

        for b in [1, 2, 3, 4]:

            lista = notas_por_disciplina[disciplina.id][b]
            notas_detalhadas[b] = lista

            if lista:
                soma = sum(n["valor"] * n["peso"] for n in lista)
                peso_total = sum(n["peso"] for n in lista)
                media = soma / peso_total
                bimestres[b] = arredondar_media_personalizada(round(media, 2))
            else:
                bimestres[b] = None

        medias_validas = [v for v in bimestres.values() if v is not None]
        media_final = round(sum(medias_validas) / len(medias_validas), 2) if medias_validas else None
        media_final = arredondar_media_personalizada(media_final)

        if media_final is None:
            status = "-"
        elif media_final >= 7:
            status = "Aprovado"
        elif media_final >= 5:
            status = "Recuperação"
        else:
            status = "Reprovado"

        boletim.append({
            "disciplina": disciplina.nome,
            "bimestres": bimestres,
            "notas": notas_detalhadas,
            "media_final": media_final,
            "faltas": faltas_por_disciplina.get(disciplina.id, 0),
            "status": status
        })

    # ================================
    # PDF
    # ================================

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="boletim_{aluno.nome}.pdf"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    AZUL_NUCLEO = colors.HexColor("#1E88E5")

    # HEADER
    elements.append(Paragraph(f"<b>BOLETIM ESCOLAR - {datetime.now().year}</b>", styles["Title"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"<b>Escola:</b> {escola.nome}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Aluno:</b> {aluno.nome}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Turma:</b> {turma.nome}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y')}", styles["Normal"]))

    elements.append(Spacer(1, 20))

    # 🔥 BLOCOS POR BIMESTRE (NOVO LAYOUT)
    for b in [1, 2, 3, 4]:

        elements.append(Paragraph(f"<b>{b}º BIMESTRE</b>", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        data = [["Disciplina", "Notas", "Média"]]

        for item in boletim:

            notas_texto = ""

            if item["notas"][b]:
                for n in item["notas"][b]:
                    notas_texto += f"{n['tipo']}: {n['valor']}<br/>"
            else:
                notas_texto = "-"

            media = item["bimestres"][b] if item["bimestres"][b] else "-"

            data.append([
                item["disciplina"],
                Paragraph(notas_texto, styles["Normal"]),
                str(media)
            ])

        table = Table(data, colWidths=[150, 220, 60])

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL_NUCLEO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

    # 🔥 RESUMO FINAL
    elements.append(Paragraph("<b>Resumo Final</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    data_final = [["Disciplina", "Média Final", "Faltas", "Situação"]]

    for item in boletim:
        data_final.append([
            item["disciplina"],
            str(item["media_final"] or "-"),
            str(item["faltas"]),
            item["status"]
        ])

    table_final = Table(data_final)

    table_final.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_NUCLEO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
    ]))

    elements.append(table_final)

    elements.append(Spacer(1, 30))

    elements.append(
        Paragraph(
            "Documento gerado automaticamente pelo sistema Núcleo Escolar",
            styles["Normal"]
        )
    )

    doc.build(elements)

    return response



# =========================================
# BOLETIM DA TURMA
# =========================================
@login_required
def boletim_turma(request, turma_id):

    turma = get_object_or_404(Turma, id=turma_id)
    escola = turma.escola

    alunos = Aluno.objects.filter(
        turma_principal=turma,
        escola=escola
    ).order_by("nome")

    avaliacoes = Avaliacao.objects.filter(
        turma=turma,
        escola=escola
    ).select_related(
        "disciplina",
        "tipo"
    )

    notas = Nota.objects.filter(
        avaliacao__in=avaliacoes,
        aluno__in=alunos
    ).select_related(
        "avaliacao",
        "avaliacao__tipo"
    )

    notas_por_aluno = defaultdict(list)

    for nota in notas:
        notas_por_aluno[nota.aluno_id].append(nota)

    resultado = []

    for aluno in alunos:

        soma = Decimal("0")
        peso_total = Decimal("0")

        for n in notas_por_aluno.get(aluno.id, []):

            peso = n.avaliacao.tipo.peso if n.avaliacao.tipo else 1

            soma += Decimal(n.valor) * Decimal(peso)
            peso_total += Decimal(peso)

        media_final = round(soma / peso_total, 2) if peso_total > 0 else None
        media_final = arredondar_media_personalizada(media_final)

        resultado.append({
            "aluno": aluno,
            "media": media_final,
            "status": "Aprovado" if media_final and media_final >= 7 else "Reprovado"
        })

    return render(request, "boletim/boletim_turma.html", {
        "turma": turma,
        "resultado": resultado
    })