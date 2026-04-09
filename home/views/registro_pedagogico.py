import json
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction

from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors

from home.models import (
    RegistroPedagogico,
    Turma,
    Docente,
    TurmaDisciplina,
    Disciplina,
)

MAX_TEXTO = 3000  # limite seguro (pode ajustar)


@login_required
def registro_pedagogico_view(request):
    """
    Tela principal do Registro Pedagógico
    - Diretor/Coordenador: vê todas as turmas da escola
    - Professor: vê apenas turmas em que está vinculado (TurmaDisciplina)
    """
    usuario = request.user
    escola = usuario.escola

    if usuario.role == "professor":
        professor = Docente.objects.filter(user=usuario, escola=escola).first()

        if professor:
            turmas = (
                Turma.objects.filter(
                    escola=escola,
                    turmadisciplina__professor=professor,
                )
                .distinct()
                .order_by("nome")
            )
        else:
            turmas = Turma.objects.none()
    else:
        turmas = Turma.objects.filter(escola=escola).order_by("nome")

    return render(
        request,
        "pages/registro_pedagogico.html",
        {
            "turmas": turmas,
            "ano_atual": date.today().year,
        },
    )


@login_required
@require_GET
def buscar_disciplinas_por_turma(request):
    usuario = request.user
    escola = usuario.escola
    turma_id = request.GET.get("turma")

    if not turma_id:
        return JsonResponse([], safe=False)

    try:
        turma = Turma.objects.get(id=turma_id, escola=escola)
    except Turma.DoesNotExist:
        return JsonResponse([], safe=False)

    if usuario.role == "professor":
        professor = Docente.objects.filter(user=usuario, escola=escola).first()
        if not professor:
            return JsonResponse([], safe=False)

        disciplinas = (
            Disciplina.objects.filter(
                turmadisciplina__turma=turma,
                turmadisciplina__professor=professor,
            )
            .distinct()
            .order_by("nome")
        )
    else:
        disciplinas = (
            Disciplina.objects.filter(
                turmadisciplina__turma=turma
            )
            .distinct()
            .order_by("nome")
        )

    data = [{"id": d.id, "nome": d.nome} for d in disciplinas]
    return JsonResponse(data, safe=False)


@login_required
@require_POST
@transaction.atomic
def salvar_registro_pedagogico(request):
    usuario = request.user
    escola = usuario.escola

    if usuario.role not in ["professor", "coordenador", "diretor"]:
        return JsonResponse({"status": "erro", "mensagem": "Acesso negado"}, status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "erro", "mensagem": "JSON inválido"},
            status=400,
        )

    turma_id = payload.get("turma")
    disciplina_id = payload.get("disciplina")
    ano_letivo = payload.get("ano_letivo")
    registros = payload.get("registros")

    if not all([turma_id, disciplina_id, ano_letivo, registros]):
        return JsonResponse(
            {"status": "erro", "mensagem": "Dados obrigatórios ausentes"},
            status=400,
        )

    try:
        ano_letivo = int(ano_letivo)
    except (TypeError, ValueError):
        return JsonResponse(
            {"status": "erro", "mensagem": "Ano letivo inválido"},
            status=400,
        )

    if ano_letivo < 2000 or ano_letivo > 2100:
        return JsonResponse(
            {"status": "erro", "mensagem": "Ano letivo fora do intervalo permitido"},
            status=400,
        )

    if not isinstance(registros, dict):
        return JsonResponse(
            {"status": "erro", "mensagem": "Formato de registros inválido"},
            status=400,
        )

    try:
        turma = Turma.objects.get(id=turma_id, escola=escola)
        disciplina = Disciplina.objects.get(id=disciplina_id)
    except (Turma.DoesNotExist, Disciplina.DoesNotExist):
        return JsonResponse(
            {"status": "erro", "mensagem": "Turma ou disciplina inválida"},
            status=404,
        )

    # Garante que a disciplina pertence à turma
    disciplina_na_turma = TurmaDisciplina.objects.filter(
        turma=turma,
        disciplina=disciplina,
        turma__escola=escola,
    ).exists()

    if not disciplina_na_turma:
        return JsonResponse(
            {"status": "erro", "mensagem": "Disciplina não vinculada a esta turma"},
            status=403,
        )

    # Professor só pode salvar nas turmas/disciplinas em que está vinculado
    if usuario.role == "professor":
        professor = Docente.objects.filter(user=usuario, escola=escola).first()
        if not professor:
            return JsonResponse({"status": "erro", "mensagem": "Professor inválido"}, status=403)

        permitido = TurmaDisciplina.objects.filter(
            professor=professor,
            turma=turma,
            disciplina=disciplina,
            turma__escola=escola,
        ).exists()

        if not permitido:
            return JsonResponse(
                {"status": "erro", "mensagem": "Registro não permitido para este professor"},
                status=403,
            )

    with transaction.atomic():
        for bimestre, texto in registros.items():
            try:
                bimestre = int(bimestre)
            except (TypeError, ValueError):
                continue

            if bimestre not in [1, 2, 3, 4]:
                continue

            if texto is None:
                texto = ""

            if not isinstance(texto, str):
                texto = str(texto)

            texto = texto.strip()

            if len(texto) > MAX_TEXTO:
                texto = texto[:MAX_TEXTO]

            RegistroPedagogico.objects.update_or_create(
                turma=turma,
                disciplina=disciplina,
                ano_letivo=ano_letivo,
                bimestre=bimestre,
                defaults={
                    "observacoes": texto,
                    "escola": escola,
                },
            )

    return JsonResponse(
        {"status": "ok", "mensagem": "Registro pedagógico salvo com sucesso"}
    )


@login_required
@require_GET
def buscar_registro_pedagogico(request):
    usuario = request.user
    escola = usuario.escola

    if usuario.role not in ["professor", "coordenador", "diretor"]:
        return JsonResponse({"erro": "Acesso negado"}, status=403)

    turma_id = request.GET.get("turma")
    disciplina_id = request.GET.get("disciplina")
    ano_letivo = request.GET.get("ano_letivo")

    if not all([turma_id, disciplina_id, ano_letivo]):
        return JsonResponse(
            {"erro": "Parâmetros obrigatórios: turma, disciplina, ano_letivo"},
            status=400
        )

    try:
        turma = Turma.objects.get(id=turma_id, escola=escola)
        disciplina = Disciplina.objects.get(id=disciplina_id)
    except (Turma.DoesNotExist, Disciplina.DoesNotExist):
        return JsonResponse({"erro": "Turma ou disciplina inválida"}, status=404)

    disciplina_na_turma = TurmaDisciplina.objects.filter(
        turma=turma,
        disciplina=disciplina,
        turma__escola=escola,
    ).exists()

    if not disciplina_na_turma:
        return JsonResponse({"erro": "Disciplina não vinculada a esta turma"}, status=403)

    if usuario.role == "professor":
        professor = Docente.objects.filter(user=usuario, escola=escola).first()
        if not professor:
            return JsonResponse({"erro": "Professor inválido"}, status=403)

        permitido = TurmaDisciplina.objects.filter(
            professor=professor,
            turma=turma,
            disciplina=disciplina,
            turma__escola=escola,
        ).exists()

        if not permitido:
            return JsonResponse({"erro": "Registro não permitido para este professor"}, status=403)

    registros = (
        RegistroPedagogico.objects
        .filter(
            turma=turma,
            disciplina=disciplina,
            ano_letivo=int(ano_letivo),
            escola=escola,
        )
        .values("bimestre", "observacoes")
    )

    resposta = {1: "", 2: "", 3: "", 4: ""}
    for r in registros:
        resposta[int(r["bimestre"])] = r["observacoes"] or ""

    return JsonResponse(resposta)


@login_required
def gerar_pdf_registro_pedagogico(request):

    usuario = request.user
    escola = usuario.escola

    turma_id = request.GET.get("turma")
    disciplina_id = request.GET.get("disciplina")
    ano_letivo = request.GET.get("ano_letivo")

    if not all([turma_id, disciplina_id, ano_letivo]):
        return HttpResponse("Parâmetros inválidos", status=400)

    turma = Turma.objects.get(id=turma_id, escola=escola)
    disciplina = Disciplina.objects.get(id=disciplina_id)

    registros = (
        RegistroPedagogico.objects
        .filter(
            turma=turma,
            disciplina=disciplina,
            ano_letivo=int(ano_letivo),
            escola=escola,
        )
        .order_by("bimestre")
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="registro_{turma.nome}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    styles = getSampleStyleSheet()
    azul = colors.HexColor("#1E88E5")

    # -------------------------------
    # ESTILOS
    # -------------------------------
    titulo_escola = ParagraphStyle(
        "titulo_escola",
        parent=styles["Title"],
        fontSize=14,
        spaceAfter=4,
    )

    titulo_relatorio = ParagraphStyle(
        "titulo_relatorio",
        parent=styles["Heading2"],
        fontSize=12,
        spaceAfter=8,
    )

    label = ParagraphStyle(
        "label",
        parent=styles["Normal"],
        fontSize=9,
        spaceAfter=2,
    )

    bimestre_style = ParagraphStyle(
        "bimestre",
        parent=styles["Heading3"],
        fontSize=10,
        textColor=azul,
        spaceAfter=4,
    )

    texto_style = ParagraphStyle(
        "texto",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        spaceAfter=10,
    )

    story = []

    # -------------------------------
    # CABEÇALHO
    # -------------------------------
    story.append(Paragraph(f"<b>{escola.nome.upper()}</b>", titulo_escola))

    story.append(Paragraph(
        "<font color='#1E88E5'>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</font>",
        styles["Normal"]
    ))

    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>REGISTRO PEDAGÓGICO</b>", titulo_relatorio))

    # -------------------------------
    # DADOS
    # -------------------------------
    story.append(Paragraph(f"<b>Turma:</b> {turma.nome}", label))
    story.append(Paragraph(f"<b>Disciplina:</b> {disciplina.nome}", label))
    story.append(Paragraph(f"<b>Ano Letivo:</b> {ano_letivo}", label))

    story.append(Spacer(1, 10))

    # -------------------------------
    # CONTEÚDO
    # -------------------------------
    if not registros.exists():
        story.append(Paragraph("Nenhum registro encontrado.", texto_style))
    else:
        for r in registros:
            story.append(Paragraph(f"<b>{r.get_bimestre_display()}</b>", bimestre_style))

            texto = r.observacoes or "Sem observações."
            story.append(Paragraph(texto, texto_style))

    # -------------------------------
    # RODAPÉ
    # -------------------------------
    story.append(Spacer(1, 15))

    story.append(Paragraph(
        "<font color='#1E88E5'>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</font>",
        styles["Normal"]
    ))

    story.append(Spacer(1, 8))

    story.append(Paragraph("__________________________________________", styles["Normal"]))
    story.append(Paragraph("Assinatura do Professor / Coordenação", label))

    doc.build(story)

    return response