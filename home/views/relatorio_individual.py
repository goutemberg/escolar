import json
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from home.models import (
    RelatorioIndividual,
    Aluno,
    Turma,
    Docente,
    TurmaDisciplina,
)

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

MAX_TEXTO = 3000  # limite seguro (pode ajustar)


@login_required
def relatorio_individual_view(request):
    usuario = request.user
    escola = usuario.escola

    # ============================
    # TURMAS
    # ============================
    if usuario.role == "professor":
        professor = Docente.objects.filter(
            user=usuario,
            escola=escola,
        ).first()

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
        turmas = Turma.objects.filter(
            escola=escola,
        ).order_by("nome")

    # ============================
    # ALUNOS DA TURMA SELECIONADA
    # ============================
    turma_id = request.GET.get("turma")

    alunos = []

    if turma_id:
        turma = Turma.objects.filter(
            id=turma_id,
            escola=escola,
        ).first()

        if turma:
            alunos = (
                Aluno.objects.filter(
                    turma_alunos__turma=turma,
                    escola=escola,
                )
                .distinct()
                .order_by("nome")
            )

    return render(
        request,
        "pages/relatorio_individual.html",
        {
            "turmas": turmas,
            "alunos": alunos,
            "turma_selecionada": turma_id,
            "ano_atual": date.today().year,
        },
    )


@login_required
@require_POST
@transaction.atomic
def salvar_relatorio_individual(request):
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

    aluno_id = payload.get("aluno")
    turma_id = payload.get("turma")
    ano_letivo = payload.get("ano_letivo")
    registros = payload.get("registros")

    if not all([aluno_id, turma_id, ano_letivo, registros]):
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
        aluno = Aluno.objects.get(id=aluno_id, escola=escola)
        turma = Turma.objects.get(id=turma_id, escola=escola)
    except (Aluno.DoesNotExist, Turma.DoesNotExist):
        return JsonResponse(
            {"status": "erro", "mensagem": "Aluno ou turma inválidos"},
            status=404,
        )

    if usuario.role == "professor":
        professor = Docente.objects.filter(user=usuario, escola=escola).first()
        if not professor:
            return JsonResponse(
                {"status": "erro", "mensagem": "Professor inválido"}, status=403
            )

        permitido = TurmaDisciplina.objects.filter(
            professor=professor,
            turma=turma,
            turma__escola=escola,
        ).exists()

        if not permitido:
            return JsonResponse(
                {
                    "status": "erro",
                    "mensagem": "Turma não permitida para este professor",
                },
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

            RelatorioIndividual.objects.update_or_create(
                aluno=aluno,
                turma=turma,
                ano_letivo=ano_letivo,
                bimestre=bimestre,
                defaults={
                    "observacoes": texto,
                    "escola": escola,
                },
            )

    return JsonResponse(
        {"status": "ok", "mensagem": "Relatório individual salvo com sucesso"}
    )


@login_required
@require_GET
def buscar_relatorio_individual(request):
    usuario = request.user
    escola = usuario.escola

    if usuario.role not in ["professor", "coordenador", "diretor"]:
        return JsonResponse({"erro": "Acesso negado"}, status=403)

    aluno_id = request.GET.get("aluno")
    turma_id = request.GET.get("turma")
    ano_letivo = request.GET.get("ano_letivo")

    if not all([aluno_id, turma_id, ano_letivo]):
        return JsonResponse(
            {"erro": "Parâmetros obrigatórios: aluno, turma, ano_letivo"}, status=400
        )

    try:
        aluno = Aluno.objects.get(id=aluno_id, escola=escola)
        turma = Turma.objects.get(id=turma_id, escola=escola)
    except (Aluno.DoesNotExist, Turma.DoesNotExist):
        return JsonResponse({"erro": "Aluno ou turma inválidos"}, status=404)

    if usuario.role == "professor":
        professor = Docente.objects.filter(user=usuario, escola=escola).first()
        if not professor:
            return JsonResponse({"erro": "Professor inválido"}, status=403)

        permitido = TurmaDisciplina.objects.filter(
            professor=professor,
            turma=turma,
            turma__escola=escola,
        ).exists()

        if not permitido:
            return JsonResponse(
                {"erro": "Turma não permitida para este professor"}, status=403
            )

    registros = RelatorioIndividual.objects.filter(
        aluno=aluno,
        turma=turma,
        ano_letivo=int(ano_letivo),
        escola=escola,
    ).values("bimestre", "observacoes")

    resposta = {1: "", 2: "", 3: "", 4: ""}
    for r in registros:
        resposta[int(r["bimestre"])] = r["observacoes"] or ""

    return JsonResponse(resposta)


from reportlab.lib import colors


@login_required
def gerar_pdf_relatorio_individual(request):
    from xml.sax.saxutils import escape

    usuario = request.user
    escola = usuario.escola

    if usuario.role not in ["professor", "coordenador", "diretor"]:
        return HttpResponse("Acesso negado", status=403)

    aluno_id = request.GET.get("aluno")
    turma_id = request.GET.get("turma")
    ano_letivo = request.GET.get("ano_letivo")

    if not all([aluno_id, turma_id, ano_letivo]):
        return HttpResponse("Parâmetros inválidos", status=400)

    # =========================================
    # BUSCA DOS DADOS
    # =========================================

    try:
        ano_letivo = int(ano_letivo)

        aluno = Aluno.objects.get(
            id=aluno_id,
            escola=escola,
        )

        turma = Turma.objects.get(
            id=turma_id,
            escola=escola,
        )

    except (ValueError, Aluno.DoesNotExist, Turma.DoesNotExist):
        return HttpResponse("Aluno, turma ou ano letivo inválido.", status=400)

    registros = RelatorioIndividual.objects.filter(
        aluno=aluno,
        turma=turma,
        ano_letivo=ano_letivo,
        escola=escola,
    ).order_by("bimestre")

    # =========================================
    # CONFIGURAÇÃO DA RESPOSTA PDF
    # =========================================

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = f'inline; filename="relatorio_{aluno.nome}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    azul = colors.HexColor("#1E88E5")

    # =========================================
    # ESTILOS
    # =========================================

    titulo_escola = ParagraphStyle(
        "titulo_escola",
        parent=styles["Title"],
        fontSize=14,
        alignment=1,
        spaceAfter=4,
    )

    titulo_relatorio = ParagraphStyle(
        "titulo_relatorio",
        parent=styles["Heading2"],
        fontSize=12,
        alignment=1,
        spaceAfter=10,
    )

    label = ParagraphStyle(
        "label",
        parent=styles["Normal"],
        fontSize=9,
        leading=14,
        spaceAfter=3,
    )

    bimestre_style = ParagraphStyle(
        "bimestre",
        parent=styles["Heading3"],
        fontSize=10,
        textColor=azul,
        leading=14,
        spaceAfter=6,
        spaceBefore=10,
    )

    texto_style = ParagraphStyle(
        "texto",
        parent=styles["Normal"],
        fontSize=9,
        leading=16,
        spaceAfter=0,
        wordWrap="LTR",
        alignment=4,
    )

    story = []

    # =========================================
    # CABEÇALHO
    # =========================================

    story.append(
        Paragraph(
            f"<b>{escape(escola.nome.upper())}</b>",
            titulo_escola,
        )
    )

    story.append(
        Paragraph(
            "<font color='#1E88E5'>" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "</font>",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 6))

    story.append(
        Paragraph(
            "<b>RELATÓRIO INDIVIDUAL</b>",
            titulo_relatorio,
        )
    )

    # =========================================
    # DADOS DO ALUNO
    # =========================================

    story.append(
        Paragraph(
            f"<b>Aluno:</b> {escape(aluno.nome)}",
            label,
        )
    )

    story.append(
        Paragraph(
            f"<b>Turma:</b> {escape(turma.nome)}",
            label,
        )
    )

    story.append(
        Paragraph(
            f"<b>Ano Letivo:</b> {ano_letivo}",
            label,
        )
    )

    story.append(Spacer(1, 12))

    # =========================================
    # CONTEÚDO DOS BIMESTRES
    # =========================================

    if not registros.exists():

        story.append(
            Paragraph(
                "Nenhum registro encontrado.",
                texto_style,
            )
        )

    else:

        for r in registros:

            story.append(
                Paragraph(
                    f"<b>{escape(r.get_bimestre_display())}</b>",
                    bimestre_style,
                )
            )

            texto = r.observacoes or "Sem observações."

            # Normaliza as quebras de linha.
            texto = texto.replace("\r\n", "\n").replace("\r", "\n")

            # Divide o conteúdo em blocos menores.
            # Cada bloco será uma linha independente da tabela,
            # permitindo a divisão entre páginas.
            paragrafos = []

            for linha in texto.split("\n"):

                linha = linha.strip()

                if not linha:
                    paragrafos.append(Paragraph("&nbsp;", texto_style))
                    continue

                palavras = linha.split()
                bloco_atual = ""

                for palavra in palavras:

                    # Trata também palavras excepcionalmente longas.
                    if len(palavra) > 450:

                        if bloco_atual:
                            paragrafos.append(
                                Paragraph(
                                    escape(bloco_atual),
                                    texto_style,
                                )
                            )
                            bloco_atual = ""

                        for inicio in range(0, len(palavra), 450):
                            trecho = palavra[inicio : inicio + 450]

                            paragrafos.append(
                                Paragraph(
                                    escape(trecho),
                                    texto_style,
                                )
                            )

                        continue

                    candidato = f"{bloco_atual} {palavra}".strip()

                    if len(candidato) > 450 and bloco_atual:

                        paragrafos.append(
                            Paragraph(
                                escape(bloco_atual),
                                texto_style,
                            )
                        )

                        bloco_atual = palavra

                    else:
                        bloco_atual = candidato

                if bloco_atual:
                    paragrafos.append(
                        Paragraph(
                            escape(bloco_atual),
                            texto_style,
                        )
                    )

            # Evita criar uma tabela sem conteúdo.
            if not paragrafos:
                paragrafos.append(Paragraph("Sem observações.", texto_style))

            # Cada parágrafo ocupa uma linha.
            # splitByRow permite dividir a tabela entre páginas.
            tabela_texto = Table(
                [[paragrafo] for paragrafo in paragrafos],
                colWidths=[17 * cm],
                splitByRow=1,
            )

            tabela_texto.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            colors.whitesmoke,
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            colors.lightgrey,
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            10,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            10,
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            5,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            5,
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),
                    ]
                )
            )

            story.append(tabela_texto)
            story.append(Spacer(1, 8))

    # =========================================
    # RODAPÉ / ASSINATURA
    # =========================================

    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            "<font color='#1E88E5'>" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "</font>",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 12))

    assinatura_tabela = Table(
        [
            ["__________________________________________"],
            ["Assinatura do Professor / Coordenação"],
        ],
        colWidths=[10 * cm],
    )

    assinatura_tabela.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(assinatura_tabela)

    # =========================================
    # GERAÇÃO DO PDF
    # =========================================

    doc.build(story)

    return response
