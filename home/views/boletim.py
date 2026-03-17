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


# =========================================
# PDF DO BOLETIM
# =========================================

def gerar_pdf_boletim(request, aluno_id):

    aluno = get_object_or_404(Aluno, id=aluno_id)
    escola = aluno.escola
    turma = aluno.turma

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

    notas_por_disciplina = defaultdict(lambda: defaultdict(list))

    for nota in notas:

        disciplina_id = nota.avaliacao.disciplina_id
        bimestre = nota.avaliacao.bimestre
        peso = nota.avaliacao.tipo.peso if nota.avaliacao.tipo else 1

        if nota.valor is not None:
            notas_por_disciplina[disciplina_id][bimestre].append(
                (float(nota.valor), float(peso))
            )

    faltas_por_disciplina = defaultdict(int)

    chamadas = Chamada.objects.filter(
        diario__turma=turma
    )

    presencas = Presenca.objects.filter(
        aluno=aluno,
        chamada__in=chamadas
    ).select_related("chamada__diario")

    for p in presencas:
        if not p.presente:
            faltas_por_disciplina[p.chamada.diario.disciplina_id] += 1

    boletim = []

    for disciplina in disciplinas:

        bimestres = {}

        for b in [1, 2, 3, 4]:

            valores = notas_por_disciplina[disciplina.id][b]

            if valores:

                soma = 0
                peso_total = 0

                for nota, peso in valores:
                    soma += nota * peso
                    peso_total += peso

                bimestres[b] = round(soma / peso_total, 2)

            else:
                bimestres[b] = None

        medias_validas = [v for v in bimestres.values() if v is not None]

        media_final = round(sum(medias_validas) / len(medias_validas), 2) if medias_validas else None

        # Situação do aluno na disciplina
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
            "b1": bimestres[1] or "-",
            "b2": bimestres[2] or "-",
            "b3": bimestres[3] or "-",
            "b4": bimestres[4] or "-",
            "media": media_final or "-",
            "faltas": faltas_por_disciplina.get(disciplina.id, 0),
            "status": status
        })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="boletim_{aluno.nome}.pdf"'

    doc = SimpleDocTemplate(response)

    elements = []
    styles = getSampleStyleSheet()

    # Cabeçalho
    elements.append(Paragraph(f"<b>BOLETIM ESCOLAR - {datetime.now().year}</b>", styles["Title"]))
    elements.append(Spacer(1, 15))

    elements.append(Paragraph(f"<b>Escola:</b> {escola.nome}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Aluno:</b> {aluno.nome}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Turma:</b> {turma.nome}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Data de emissão:</b> {datetime.now().strftime('%d/%m/%Y')}", styles["Normal"]))

    elements.append(Spacer(1, 20))

    data = [["Disciplina", "1º", "2º", "3º", "4º", "Média", "Faltas", "Situação"]]

    for item in boletim:

        data.append([
            item["disciplina"],
            item["b1"],
            item["b2"],
            item["b3"],
            item["b4"],
            item["media"],
            item["faltas"],
            item["status"]
        ])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([

        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fab982")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

        ("ALIGN", (1, 1), (-2, -1), "CENTER"),
        ("ALIGN", (-1, 1), (-1, -1), "CENTER"),

        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.whitesmoke,
            colors.lightgrey
        ]),

    ]))

    elements.append(table)

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

        resultado.append({
            "aluno": aluno,
            "media": media_final,
            "status": "Aprovado" if media_final and media_final >= 7 else "Reprovado"
        })

    return render(request, "boletim/boletim_turma.html", {
        "turma": turma,
        "resultado": resultado
    })