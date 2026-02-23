from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from django.http import HttpResponse
from datetime import datetime
from django.shortcuts import render

from home.models import Aluno, Avaliacao, Disciplina, Nota

from collections import defaultdict


def gerar_pdf_boletim(request, aluno_id):

    aluno = Aluno.objects.get(id=aluno_id)
    escola = aluno.escola

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="boletim_{aluno.nome}.pdf"'

    doc = SimpleDocTemplate(response)
    elements = []

    styles = getSampleStyleSheet()

    # Título
    elements.append(Paragraph(f"<b>BOLETIM ESCOLAR - {datetime.now().year}</b>", styles['Title']))
    elements.append(Spacer(1, 0.3 * inch))

    # Dados da escola
    elements.append(Paragraph(f"<b>Escola:</b> {escola.nome}", styles['Normal']))
    elements.append(Paragraph(f"<b>CNPJ:</b> {escola.cnpj}", styles['Normal']))
    elements.append(Paragraph(f"<b>Cidade:</b> {escola.cidade} - {escola.estado}", styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    # Dados do aluno
    elements.append(Paragraph(f"<b>Aluno:</b> {aluno.nome}", styles['Normal']))
    elements.append(Paragraph(f"<b>CPF:</b> {aluno.cpf}", styles['Normal']))
    elements.append(Spacer(1, 0.4 * inch))

    # Organização das notas
    boletim = defaultdict(lambda: defaultdict(list))

    avaliacoes = Avaliacao.objects.filter(escola=escola)

    for av in avaliacoes:
        nota = Nota.objects.filter(avaliacao=av, aluno=aluno).first()
        if nota:
            boletim[av.disciplina.nome][av.bimestre].append(
                nota.valor * av.tipo.peso
            )

    # Tabela
    data = [["Disciplina", "1º", "2º", "3º", "4º", "Média Final"]]

    for disciplina, bimestres in boletim.items():

        medias = []
        for i in range(1, 5):
            notas = bimestres.get(i, [])
            if notas:
                media = round(sum(notas) / len(notas), 2)
            else:
                media = "-"
            medias.append(media)

        medias_validas = [m for m in medias if isinstance(m, (int, float))]
        media_final = round(sum(medias_validas) / len(medias_validas), 2) if medias_validas else "-"

        data.append([
            disciplina,
            medias[0],
            medias[1],
            medias[2],
            medias[3],
            media_final
        ])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#fab982")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
    ]))

    elements.append(table)

    doc.build(elements)

    return response


def boletim_turma(request, turma_id):

    turma = Turma.objects.get(id=turma_id)
    alunos = turma.alunos.all()

    resultado = []

    for aluno in alunos:
        medias = []

        avaliacoes = Avaliacao.objects.filter(escola=turma.escola)

        for av in avaliacoes:
            nota = Nota.objects.filter(avaliacao=av, aluno=aluno).first()
            if nota:
                medias.append(nota.valor * av.tipo.peso)

        media_final = round(sum(medias)/len(medias), 2) if medias else None

        resultado.append({
            "aluno": aluno,
            "media": media_final,
            "status": "Aprovado" if media_final and media_final >= 7 else "Reprovado"
        })

    return render(request, "boletim/boletim_turma.html", {
        "turma": turma,
        "resultado": resultado
    })
