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
from django.shortcuts import render, redirect
from django.db.models import Q
# =========================================
# PDF DO BOLETIM
# =========================================

@login_required
def gerar_pdf_boletim(request, aluno_id, turma_id):

    aluno = get_object_or_404(Aluno, id=aluno_id)
    turma = get_object_or_404(Turma, id=turma_id)
    escola = turma.escola

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

    # 🔥 NOTAS POR DISCIPLINA
    notas_por_disciplina = defaultdict(lambda: defaultdict(list))

    for nota in notas:
        disciplina_id = nota.avaliacao.disciplina_id
        bimestre = nota.avaliacao.bimestre
        peso = nota.avaliacao.tipo.peso if nota.avaliacao.tipo else 1

        # 🔥 TRATAMENTO COMPLETO (NUM + CON)
        if nota.valor is not None:
            valor_exibicao = float(nota.valor)

        elif nota.conceito:
            valor_exibicao = nota.conceito

        else:
            continue

        notas_por_disciplina[disciplina_id][bimestre].append({
            "valor": valor_exibicao,
            "peso": float(peso),
            "tipo": nota.avaliacao.tipo.nome if nota.avaliacao.tipo else "Avaliação"
        })

    # 🔥 FALTAS
    faltas_por_disciplina = defaultdict(int)

    chamadas = Chamada.objects.filter(diario__turma=turma)

    presencas = Presenca.objects.filter(
        aluno=aluno,
        chamada__in=chamadas
    ).select_related("chamada__diario")

    for p in presencas:
        if not p.presente:
            faltas_por_disciplina[p.chamada.diario.disciplina_id] += 1

    # 🔥 BOLETIM FINAL
    boletim = []

    for disciplina in disciplinas:

        bimestres = {}
        notas_detalhadas = {}

        for b in [1, 2, 3, 4]:

            lista = notas_por_disciplina[disciplina.id][b]
            notas_detalhadas[b] = lista

            # 🔥 SÓ CALCULA MÉDIA SE FOR NUMÉRICO
            valores_validos = [n for n in lista if isinstance(n["valor"], (int, float))]

            if valores_validos:
                soma = sum(n["valor"] * n["peso"] for n in valores_validos)
                peso_total = sum(n["peso"] for n in valores_validos)
                media = soma / peso_total
                bimestres[b] = arredondar_media_personalizada(round(media, 2))
            else:
                bimestres[b] = None

        medias_validas = [v for v in bimestres.values() if v is not None]

        media_final = (
            round(sum(medias_validas) / len(medias_validas), 2)
            if medias_validas else None
        )

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

    elements.append(Paragraph(f"<b>BOLETIM ESCOLAR - {datetime.now().year}</b>", styles["Title"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"<b>Escola:</b> {escola.nome}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Aluno:</b> {aluno.nome}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Turma:</b> {turma.nome}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y')}", styles["Normal"]))

    elements.append(Spacer(1, 20))

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
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

    doc.build(elements)

    return response



# =========================================
# BOLETIM DA TURMA
# =========================================
@login_required
def boletim_turma(request, turma_id):

    turma = get_object_or_404(
        Turma,
        id=turma_id,
        escola=request.user.escola  # 🔥 garante isolamento multi-escola
    )

    escola = turma.escola

    alunos = Aluno.objects.filter(
        turma_principal=turma,
        escola=escola,
        ativo=True  # 🔥 evita lixo
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


@login_required
def boletim(request, aluno_id, turma_id):

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=request.user.escola
    )

    turma = get_object_or_404(
        Turma,
        id=turma_id,
        escola=request.user.escola
    )

    # DECIDE COM BASE NA TURMA ESCOLHIDA
    if turma.sistema_avaliacao == "CON":
        return redirect("boletim_infantil", aluno_id=aluno.id, turma_id=turma.id)

    else:
        return redirect("gerar_pdf_boletim", aluno_id=aluno.id, turma_id=turma.id)



@login_required
def escolher_turma_boletim(request, aluno_id):

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=request.user.escola
    )

    # 🔥 pega TODAS as turmas do aluno (principal + adicionais)
    turmas = Turma.objects.filter(
        Q(alunos=aluno) | Q(id=aluno.turma_principal_id),
        escola=request.user.escola
    ).distinct().order_by("nome")

    return render(request, "pages/escolher_turma_boletim.html", {
        "aluno": aluno,
        "turmas": turmas
    })


@login_required
def boletim_aluno_redirect(request, aluno_id):

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=request.user.escola
    )

    # 🔥 tenta turma principal ou M2M direto
    turma = aluno.turma_principal or aluno.turmas.first()

    # 🔥 fallback completo (garante pegar mesmo com banco inconsistente)
    if not turma:
        turma = Turma.objects.filter(
            Q(alunos=aluno),
            escola=request.user.escola
        ).order_by("id").first()

    # 🔥 se ainda não encontrou, força escolha manual
    if not turma:
        return redirect("escolher_turma_boletim", aluno_id=aluno.id)

    print("TURMA_ID:", turma.id)  # mantém seu log

    # 🔥 redireciona conforme tipo de avaliação
    sistema = (getattr(turma, "sistema_avaliacao", None) or "NUM").upper()

    if sistema == "CON":
        return redirect("boletim_infantil", aluno_id=aluno.id, turma_id=turma.id)

    return redirect("gerar_pdf_boletim", aluno_id=aluno.id, turma_id=turma.id)