# ============================================
# 📌 IMPORTS — DIÁRIO DE CLASSE / PDF OFICIAL
# ============================================

# ---- Standard Library ----
import json
from io import BytesIO
from datetime import date

# ---- Django Core ----
from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone

# ---- Permissões ----
from home.decorators import role_required

# ---- Models ----
from home.models import (
    TurmaDisciplina,
    DiarioDeClasse,
    Turma,
    Disciplina,
    Docente,
)

# ---- PDF (ReportLab - PRODUÇÃO SAFE) ----
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---- Datas PT-BR ----
from babel.dates import format_date


@login_required
@role_required(["professor", "coordenador", "diretor"])
def api_disciplinas_por_turma(request, turma_id):
    user = request.user

    qs = TurmaDisciplina.objects.filter(
        turma_id=turma_id,
        turma__escola=user.escola
    )

    # professor vê apenas o que leciona
    if user.role == "professor":
        try:
            qs = qs.filter(professor=user.docente)
        except Exception:
            return JsonResponse([], safe=False)

    disciplinas = (
        qs.select_related("disciplina")
          .values("disciplina__id", "disciplina__nome")
          .distinct()
    )

    data = [
        {
            "id": d["disciplina__id"],
            "nome": d["disciplina__nome"]
        }
        for d in disciplinas
    ]

    return JsonResponse(data, safe=False)

@login_required
def api_listar_diario(request):
    turma_id = request.GET.get("turma")
    disciplina_id = request.GET.get("disciplina")
    mes = request.GET.get("mes")  # formato: YYYY-MM

    if not (turma_id and disciplina_id and mes):
        return JsonResponse([], safe=False)

    ano, mes_num = mes.split("-")

    diarios = (
        DiarioDeClasse.objects
        .filter(
            turma_id=turma_id,
            disciplina_id=disciplina_id,
            data_ministrada__year=int(ano),
            data_ministrada__month=int(mes_num),
            escola=request.user.escola
        )
        .order_by("data_ministrada", "hora_inicio")
    )

    data = [
        {
            "id": d.id,
            "data_ministrada": d.data_ministrada.isoformat(),
            "hora_inicio": d.hora_inicio.strftime("%H:%M") if d.hora_inicio else "",
            "hora_fim": d.hora_fim.strftime("%H:%M") if d.hora_fim else "",
            "resumo_conteudo": d.resumo_conteudo
        }
        for d in diarios
    ]

    return JsonResponse(data, safe=False)



@login_required
@require_POST
def salvar_diario_classe(request):
    try:
        payload = json.loads(request.body)

        diario_id = payload.get("id")
        turma_id = payload.get("turma")
        disciplina_id = payload.get("disciplina")
        data_ministrada = payload.get("data_ministrada")
        hora_inicio = payload.get("hora_inicio")
        hora_fim = payload.get("hora_fim")
        resumo_conteudo = payload.get("resumo_conteudo", "").strip()

        if not all([turma_id, disciplina_id, data_ministrada, resumo_conteudo]):
            return JsonResponse(
                {"error": "Campos obrigatórios não informados."},
                status=400
            )

        # converte data
        data_ministrada_date = date.fromisoformat(data_ministrada)

        turma = Turma.objects.get(
            id=turma_id,
            escola=request.user.escola
        )

        disciplina = Disciplina.objects.get(id=disciplina_id)

        # =========================
        # CONTROLE DE PERMISSÃO
        # =========================

        professor_obj = None

        if request.user.role == "professor":
            try:
                professor_obj = request.user.docente
            except Docente.DoesNotExist:
                return JsonResponse(
                    {"error": "Professor sem vínculo com docente."},
                    status=403
                )

            # garante que o professor leciona a turma/disciplina
            if not turma.turmadisciplina_set.filter(
                professor=professor_obj,
                disciplina=disciplina
            ).exists():
                return JsonResponse(
                    {"error": "Acesso não autorizado para esta turma/disciplina."},
                    status=403
                )

            # 🔒 REGRA PEDAGÓGICA
            if data_ministrada_date < date.today():
                return JsonResponse(
                    {
                        "error": (
                            "Aulas de datas anteriores não podem ser "
                            "editadas por professores."
                        )
                    },
                    status=403
                )

        # =========================
        # CREATE ou UPDATE
        # =========================

        if diario_id:
            diario = DiarioDeClasse.objects.get(
                id=diario_id,
                escola=request.user.escola
            )
        else:
            diario = DiarioDeClasse(
                escola=request.user.escola,
                criado_por=request.user
            )

        diario.turma = turma
        diario.disciplina = disciplina
        diario.data_ministrada = data_ministrada_date
        diario.hora_inicio = hora_inicio or None
        diario.hora_fim = hora_fim or None
        diario.resumo_conteudo = resumo_conteudo

        if professor_obj:
            diario.professor = professor_obj

        diario.save()

        return JsonResponse(
            {"id": diario.id},
            status=200
        )

    except Turma.DoesNotExist:
        return JsonResponse(
            {"error": "Turma inválida."},
            status=404
        )

    except Disciplina.DoesNotExist:
        return JsonResponse(
            {"error": "Disciplina inválida."},
            status=404
        )

    except DiarioDeClasse.DoesNotExist:
        return JsonResponse(
            {"error": "Registro não encontrado."},
            status=404
        )

    except Exception as e:
        return JsonResponse(
            {
                "error": "Erro interno ao salvar diário.",
                "detail": str(e)
            },
            status=500
        )
    
@login_required
@require_GET
def diario_classe_pdf(request):
    try:
        turma_id = request.GET.get("turma")
        disciplina_id = request.GET.get("disciplina")
        mes = request.GET.get("mes")  # YYYY-MM

        if not all([turma_id, disciplina_id, mes]):
            return HttpResponseBadRequest("Parâmetros obrigatórios ausentes.")

        turma = get_object_or_404(
            Turma,
            id=turma_id,
            escola=request.user.escola
        )

        disciplina = get_object_or_404(
            Disciplina,
            id=disciplina_id
        )

        ano, mes_num = map(int, mes.split("-"))

        diarios = (
            DiarioDeClasse.objects
            .filter(
                escola=request.user.escola,
                turma=turma,
                disciplina=disciplina,
                data_ministrada__year=ano,
                data_ministrada__month=mes_num,
            )
            .select_related("professor")
            .order_by("data_ministrada", "hora_inicio")
        )

        # ============================
        # 📄 PDF CONFIG
        # ============================

        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()

        titulo_style = ParagraphStyle(
            "Titulo",
            parent=styles["Heading1"],
            alignment=1,
            spaceAfter=12,
        )

        meta_style = ParagraphStyle(
            "Meta",
            parent=styles["Normal"],
            alignment=1,
            spaceAfter=18,
        )

        conteudo_style = ParagraphStyle(
            "Conteudo",
            parent=styles["Normal"],
            wordWrap="CJK",
            leading=14,
        )

        status_style = ParagraphStyle(
            "Status",
            parent=styles["Normal"],
            alignment=1,
            fontSize=9,
        )

        elements = []

        # ============================
        # 🏫 CABEÇALHO
        # ============================

        elements.append(Paragraph("Diário de Classe", titulo_style))

        mes_formatado = format_date(
            date(ano, mes_num, 1),
            format="MMMM 'de' yyyy",
            locale="pt_BR",
        ).capitalize()

        elements.append(
            Paragraph(
                f"""
                <b>{request.user.escola.nome}</b><br/>
                Turma: {turma.nome} &nbsp;|&nbsp;
                Disciplina: {disciplina.nome}<br/>
                Mês: {mes_formatado}<br/>
                Emissão: {timezone.localtime().strftime("%d/%m/%Y %H:%M")}
                """,
                meta_style,
            )
        )

        # ============================
        # 📊 TABELA
        # ============================

        tabela_data = [
            ["#", "Data", "Horário", "Conteúdo", "Status"]
        ]

        def fmt_hora(h):
            return h.strftime("%H:%M") if h else "-"

        for idx, d in enumerate(diarios, start=1):
            horario = f"{fmt_hora(d.hora_inicio)} – {fmt_hora(d.hora_fim)}"

            conteudo = Paragraph(
                d.resumo_conteudo.replace("\n", "<br/>"),
                conteudo_style
            )

            status = Paragraph(
                "<b>🔒 Aula Fechada</b>",
                status_style
            )

            tabela_data.append([
                idx,
                d.data_ministrada.strftime("%d/%m/%Y"),
                horario,
                conteudo,
                status,
            ])

        tabela = Table(
            tabela_data,
            colWidths=[1.2 * cm, 3 * cm, 4 * cm, 7 * cm, 3 * cm],
            repeatRows=1,
        )

        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fab982")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (1, 1), (2, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ]))

        elements.append(tabela)
        elements.append(Spacer(1, 2 * cm))

        # ============================
        # ✍️ ASSINATURAS
        # ============================

        assinatura_tabela = Table(
            [
                [
                    "______________________________\nProfessor Responsável",
                    "______________________________\nCoordenação / Direção",
                ]
            ],
            colWidths=[8 * cm, 8 * cm],
        )

        assinatura_tabela.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 25),
        ]))

        elements.append(assinatura_tabela)

        # ============================
        # 🚀 BUILD
        # ============================

        doc.build(elements)

        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="diario_classe_{turma.nome}_{mes}.pdf"'
        )

        return response

    except Exception as e:
        return HttpResponse(
            f"Erro ao gerar PDF: {str(e)}",
            status=500
        )
