from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from datetime import datetime
from home.models import Aluno, Turma, Boletim
from home.utils import arredondar_media_personalizada
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Q
from home.utils import montar_boletim
from home.boletim_service import gerar_e_salvar_boletim
from django.core.files.base import ContentFile
from io import BytesIO
from django.http import JsonResponse, HttpResponse
import os

# =========================================
# PDF DO BOLETIM
# =========================================

@login_required
def gerar_pdf_boletim(request, aluno_id, turma_id):

    # ================================
    # DADOS BASE
    # ================================
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

    escola = turma.escola

    # ================================
    # 🔥 BOLETIM (CACHE + JSON)
    # ================================
    boletim_obj = gerar_e_salvar_boletim(aluno, turma)
    boletim = boletim_obj.dados

    # ================================
    # ⚡ NÃO GERAR SE JÁ EXISTE
    # ================================
    if boletim_obj.pdf:
        caminho = boletim_obj.pdf.path

    # 🔥 verifica se o arquivo realmente existe
        if os.path.exists(caminho):
            return HttpResponse(pdf, content_type="application/pdf")
        else:
        # 💥 PDF quebrado → limpa
            boletim_obj.pdf.delete(save=False)
            boletim_obj.save()

    # ================================
    # 🚀 GERAR PDF EM MEMÓRIA
    # ================================
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
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

    # ================================
    # BIMESTRES
    # ================================
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

            media = item["bimestres"][b] if item["bimestres"][b] is not None else "-"

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

    # ================================
    # BUILD PDF
    # ================================
    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    # ================================
    # 💾 SALVAR PDF
    # ================================
    boletim_obj.pdf.save(
        f"boletim_{aluno.id}_{turma.id}.pdf",
        ContentFile(pdf)
    )

    # ================================
    # 📤 RETORNAR PDF
    # ================================
    return HttpResponse(pdf, content_type="application/pdf")


# =========================================
# BOLETIM DA TURMA
# =========================================
@login_required
def boletim_turma(request, turma_id):

    turma = get_object_or_404(
        Turma,
        id=turma_id,
        escola=request.user.escola
    )

    alunos = Aluno.objects.filter(
        turma_principal=turma,
        escola=turma.escola,
        ativo=True
    ).order_by("nome")

    resultado = []

    for aluno in alunos:

        boletim_obj = gerar_e_salvar_boletim(aluno, turma)
        boletim = boletim_obj.dados

        medias = [
            d["media_final"]
            for d in boletim
            if d["media_final"] is not None
        ]

        media_final = None

        if medias:
            media_final = sum(medias) / len(medias)
            media_final = arredondar_media_personalizada(media_final)

        resultado.append({
            "aluno": aluno,
            "media": media_final,
            "status": (
                "Aprovado" if media_final and media_final >= 7
                else "Recuperação" if media_final and media_final >= 5
                else "Reprovado"
            )
        })

    return render(request, "boletim/boletim_turma.html", {
        "turma": turma,
        "resultado": resultado
    })


@login_required
def boletim(request, aluno_id, turma_id=None):

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=request.user.escola
    )

    turma = None

    if turma_id:
        turma = Turma.objects.filter(
            id=turma_id,
            escola=request.user.escola
        ).first()

    if not turma:
        turma = aluno.turma_principal

    if not turma:
        turma = aluno.turmas.first()

    if not turma:
        return redirect("listar_turmas_para_boletim")

    # 🔥 PROTEÇÃO EXTRA
    if not turma.id:
        return redirect("listar_turmas_para_boletim")

    sistema = (getattr(turma, "sistema_avaliacao", None) or "NUM").upper()

    if sistema == "CON":
        return redirect("boletim_infantil", aluno_id=aluno.id, turma_id=turma.id)

    return redirect("gerar_pdf_boletim", aluno_id=aluno.id, turma_id=turma.id)



@login_required
def escolher_turma_boletim(request, aluno_id):

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=request.user.escola
    )

    turmas = Turma.objects.filter(
        Q(alunos=aluno) | Q(alunos_principais=aluno),
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

    turma = aluno.turma_principal or aluno.turmas.first()

    if not turma:
        turma = Turma.objects.filter(
            Q(alunos=aluno),
            escola=request.user.escola
        ).order_by("id").first()

    if not turma:
        return redirect("escolher_turma_boletim", aluno_id=aluno.id)

    sistema = (getattr(turma, "sistema_avaliacao", None) or "NUM").upper()

    if sistema == "CON":
        return redirect("boletim_infantil", aluno_id=aluno.id, turma_id=turma.id)

    return redirect("gerar_pdf_boletim", aluno_id=aluno.id, turma_id=turma.id)


@login_required
def baixar_boletim(request, aluno_id):

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=request.user.escola
    )

    turma = aluno.turma_principal or aluno.turmas.first()

    if not turma:
        return JsonResponse({"erro": "Aluno sem turma."}, status=400)

    boletim = Boletim.objects.filter(
        aluno=aluno,
        turma=turma
    ).first()

    # 🔥 SE NÃO EXISTE → NÃO GERA
    if not boletim or not boletim.pdf:
        return JsonResponse({
            "erro": "Boletim ainda não foi gerado."
        }, status=404)

    # 🔥 DOWNLOAD DIRETO
    return redirect(boletim.pdf.url)