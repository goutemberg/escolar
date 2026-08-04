from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, IntegrityError
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator


import csv

from openpyxl import Workbook
from openpyxl.styles import (
    Alignment,
    Border,
    Font,
    PatternFill,
    Side,
)

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from django.db.models import Count, Q
from django.utils import timezone
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
import csv
from openpyxl import Workbook
from django.db.models import Q, OuterRef, Subquery, F

from home.models import Chamada
from django.core.paginator import Paginator

import io
import json
from datetime import datetime

from home.models import (
    Turma,
    Disciplina,
    Docente,
    TurmaDisciplina,
    Chamada,
    Presenca,
    Aluno,
    DiarioDeClasse,
)

import logging

logger = logging.getLogger(__name__)

# ======================================================
# Funções auxiliares
# ======================================================


def user_has_role(user, roles):
    if isinstance(roles, str):
        roles = [r.strip() for r in roles.split(",")]
    return hasattr(user, "role") and user.role in roles


def get_professor_or_gestor(user):
    professor = Docente.objects.filter(user=user).first()
    if professor:
        return professor

    if user_has_role(user, ["diretor", "coordenador"]):
        return None

    return "bloqueado"


# ======================================================
# 1) TELA PRINCIPAL DE CHAMADA
# ======================================================
@login_required
def tela_chamada(request):
    user = request.user

    # -------------------------------------------------
    # Papéis permitidos
    # -------------------------------------------------
    roles_permitidos = ["professor", "coordenador", "diretor"]

    if user.role not in roles_permitidos:
        return HttpResponseForbidden("Acesso negado.")

    hoje = datetime.now().date().strftime("%Y-%m-%d")

    # -------------------------------------------------
    # PROFESSOR
    # -------------------------------------------------
    if user.role == "professor":
        prof_obj = Docente.objects.filter(user=user, escola=user.escola).first()

        if not prof_obj:
            return HttpResponseForbidden("Professor sem vínculo docente.")

        turmas_disciplinas = TurmaDisciplina.objects.filter(
            professor=prof_obj, escola=user.escola
        ).select_related("turma", "disciplina")

    # -------------------------------------------------
    # COORDENADOR / DIRETOR
    # -------------------------------------------------
    else:
        turmas_disciplinas = TurmaDisciplina.objects.filter(
            escola=user.escola
        ).select_related("turma", "disciplina")

    # -------------------------------------------------
    # Extrair listas sem duplicação
    # -------------------------------------------------
    turmas = sorted({td.turma for td in turmas_disciplinas}, key=lambda t: t.nome)

    disciplinas = sorted(
        {td.disciplina for td in turmas_disciplinas}, key=lambda d: d.nome
    )

    datas_chamadas = (
        Chamada.objects.filter(escola=user.escola)
        .values_list("data", flat=True)
        .distinct()
    )

    return render(
        request,
        "pages/chamada/realizar_chamadas.html",
        {
            "turmas": turmas,
            "disciplinas": disciplinas,
            "data_hoje": hoje,
            "datas_chamadas": datas_chamadas,
        },
    )


# ======================================================
# 2) API – CARREGAR ALUNOS DA TURMA
# ======================================================
@login_required
def api_carregar_alunos(request, turma_id):

    try:
        turma = Turma.objects.get(
            id=turma_id,
            escola=request.escola,
        )
    except Turma.DoesNotExist:
        return JsonResponse(
            {"erro": "Turma não encontrada."},
            status=404,
        )

    # =====================================================
    # ALUNOS DA TURMA
    # =====================================================
    alunos_qs = turma.alunos.filter(ativo=True).order_by("nome")

    alunos = list(
        alunos_qs.values(
            "id",
            "nome",
        )
    )

    data_aula = request.GET.get("data")
    disciplina_id = request.GET.get("disciplina")

    # =====================================================
    # SEM CONTEXTO -> RETORNA APENAS ALUNOS
    # =====================================================
    if not data_aula or not disciplina_id:
        return JsonResponse({"alunos": alunos})

    # =====================================================
    # VALIDAR DATA
    # =====================================================
    try:
        data_aula_dt = datetime.strptime(
            data_aula,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return JsonResponse({"alunos": alunos})

    # =====================================================
    # VALIDAR DISCIPLINA
    # =====================================================
    try:
        disciplina = Disciplina.objects.get(
            id=disciplina_id,
            escola=request.escola,
        )
    except Disciplina.DoesNotExist:
        return JsonResponse({"alunos": alunos})

    # =====================================================
    # NOVO FLUXO:
    # PROCURA DIRETAMENTE A CHAMADA
    # =====================================================
    chamada = (
        Chamada.objects.filter(
            escola=request.escola,
            turma=turma,
            disciplina=disciplina,
            data=data_aula_dt,
        )
        .order_by("-id")
        .first()
    )

    # =====================================================
    # COMPATIBILIDADE COM DADOS ANTIGOS
    # =====================================================
    if not chamada:

        diario = (
            DiarioDeClasse.objects.filter(
                escola=request.escola,
                turma=turma,
                disciplina=disciplina,
                data_ministrada=data_aula_dt,
            )
            .order_by("-id")
            .first()
        )

        if diario:
            chamada = Chamada.objects.filter(diario=diario).order_by("-id").first()

    # =====================================================
    # MAPEAR PRESENÇAS
    # =====================================================
    presencas_map = {}

    if chamada:

        presencas = Presenca.objects.filter(chamada=chamada).values(
            "aluno_id",
            "status",
            "presente",
            "observacao",
        )

        for p in presencas:

            status = p.get("status")

            # Compatibilidade com registros antigos
            if not status:
                status = "P" if p.get("presente") else "F"

            presencas_map[p["aluno_id"]] = {
                "status": status,
                "observacao": p.get("observacao") or "",
            }

    # =====================================================
    # MONTAR RESPOSTA
    # =====================================================
    for aluno in alunos:

        extra = presencas_map.get(aluno["id"])

        if extra:
            aluno["status"] = extra["status"]
            aluno["observacao"] = extra["observacao"]

        else:
            # padrão continua sendo presente
            aluno["status"] = "P"
            aluno["observacao"] = ""

    return JsonResponse(
        {
            "alunos": alunos,
        }
    )


# ======================================================
# 3) SALVAR PRESENÇAS
# ======================================================
@csrf_exempt
@login_required
def salvar_presencas(request):
    logger.warning("====== SALVAR PRESENCAS ======")
    logger.warning(f"USER: {request.user}")
    logger.warning(f"ROLE: {getattr(request.user, 'role', None)}")
    logger.warning(f"METHOD: {request.method}")
    logger.warning(f"BODY: {request.body}")

    acesso = get_professor_or_gestor(request.user)

    if acesso == "bloqueado":
        return JsonResponse(
            {"status": "erro", "mensagem": "Acesso negado."}, status=403
        )

    if request.method != "POST":
        return JsonResponse(
            {"status": "erro", "mensagem": "Método não permitido"}, status=405
        )

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "erro", "mensagem": "JSON inválido"}, status=400)

    turma_id = data.get("turma")
    disciplina_id = data.get("disciplina")
    data_aula = data.get("data")
    lista = data.get("lista", [])

    if not turma_id or not disciplina_id or not data_aula:
        return JsonResponse(
            {"status": "erro", "mensagem": "Campos obrigatórios faltando."}, status=400
        )

    professor = None

    if acesso == "professor":
        professor = Docente.objects.filter(
            user=request.user, escola=request.escola
        ).first()

        if not professor:
            return JsonResponse(
                {
                    "status": "erro",
                    "mensagem": "Professor não está vinculado corretamente.",
                },
                status=400,
            )

    try:
        turma = Turma.objects.get(id=turma_id, escola=request.escola)
    except Turma.DoesNotExist:
        return JsonResponse(
            {"status": "erro", "mensagem": "Turma inválida."}, status=404
        )

    try:
        disciplina = Disciplina.objects.get(id=disciplina_id, escola=request.escola)
    except Disciplina.DoesNotExist:
        return JsonResponse(
            {"status": "erro", "mensagem": "Disciplina inválida."}, status=404
        )

    # Professor só pode lançar chamada das turmas/disciplina dele
    if acesso == "professor":
        permitido = TurmaDisciplina.objects.filter(
            turma=turma, disciplina=disciplina, professor=professor
        ).exists()

        if not permitido:
            return JsonResponse(
                {
                    "status": "erro",
                    "mensagem": (
                        "Você não está vinculado a esta " "disciplina nesta turma."
                    ),
                },
                status=403,
            )

    try:
        data_aula = datetime.strptime(data_aula, "%Y-%m-%d").date()

    except ValueError:
        return JsonResponse(
            {"status": "erro", "mensagem": "Data inválida."}, status=400
        )

    erros_alunos = []

    try:
        with transaction.atomic():

            # =====================================================
            # CHAMADA AGORA É INDEPENDENTE DO DIÁRIO
            # =====================================================
            chamada, _ = Chamada.objects.get_or_create(
                turma=turma,
                disciplina=disciplina,
                professor=(professor if acesso == "professor" else None),
                data=data_aula,
                escola=turma.escola,
                defaults={
                    "criado_por": request.user,
                },
            )

            # =====================================================
            # SALVAR PRESENÇAS
            # =====================================================
            for item in lista:

                aluno_id = item.get("aluno_id")

                status = item.get("status", "").strip().upper()

                # Compatibilidade com versão antiga
                if status not in ("P", "F", "J"):
                    presente_bool = bool(item.get("presente", False))
                    status = "P" if presente_bool else "F"

                presente = status == "P"

                observacao = (item.get("observacao") or "").strip()

                try:
                    aluno = Aluno.objects.get(id=aluno_id, escola=request.escola)

                except Aluno.DoesNotExist:
                    erros_alunos.append(
                        {"aluno_id": aluno_id, "mensagem": "Aluno não encontrado."}
                    )
                    continue

                Presenca.objects.update_or_create(
                    chamada=chamada,
                    aluno=aluno,
                    defaults={
                        "status": status,
                        "presente": presente,
                        "observacao": observacao,
                    },
                )

    except IntegrityError:
        return JsonResponse(
            {
                "status": "erro",
                "mensagem": ("Erro de integridade ao salvar " "a chamada."),
            },
            status=400,
        )

    except Exception as e:
        logger.exception("Erro ao salvar chamada")

        return JsonResponse(
            {
                "status": "erro",
                "mensagem": "Erro ao salvar chamada.",
                "detalhe": str(e),
            },
            status=500,
        )

    if erros_alunos:
        return JsonResponse({"status": "parcial", "erros": erros_alunos}, status=207)

    return JsonResponse({"status": "sucesso", "mensagem": "Chamada salva com sucesso!"})


@login_required
def disciplinas_por_turma(request, turma_id):
    turma = get_object_or_404(Turma, id=turma_id, escola=request.escola)

    qs = TurmaDisciplina.objects.filter(turma=turma).select_related("disciplina")

    disciplinas = [{"id": td.disciplina.id, "nome": td.disciplina.nome} for td in qs]

    return JsonResponse(disciplinas, safe=False)


# ======================================================
# 4) HISTÓRICO DE CHAMADAS
# ======================================================
@login_required
def listar_chamadas(request):

    user = request.user
    hoje = datetime.now().date()
    hoje_str = hoje.strftime("%Y-%m-%d")

    filtro_data = request.GET.get("data")
    filtro_turma = request.GET.get("turma")
    filtro_disciplina = request.GET.get("disciplina")

    sem_filtros = not filtro_data and not filtro_turma and not filtro_disciplina

    professor = Docente.objects.filter(user=user, escola=user.escola).first()

    # =====================================================
    # PERFIL PROFESSOR
    # =====================================================
    if user.role == "professor" and professor:

        turmas = (
            Turma.objects.filter(
                turmadisciplina__professor=professor,
                escola=user.escola,
            )
            .distinct()
            .order_by("nome")
        )

        disciplinas = (
            Disciplina.objects.filter(
                turmadisciplina__professor=professor,
                escola=user.escola,
            )
            .distinct()
            .order_by("nome")
        )

        turmas_ids = list(turmas.values_list("id", flat=True))

        disciplinas_ids = list(disciplinas.values_list("id", flat=True))

        # ==============================================
        # NOVA ESTRUTURA
        # ==============================================
        base = Chamada.objects.filter(
            escola=user.escola,
            turma_id__in=turmas_ids,
            disciplina_id__in=disciplinas_ids,
        )

        # Professor enxerga apenas suas chamadas
        # ou chamadas antigas sem professor definido
        base = base.filter(Q(professor=professor) | Q(professor__isnull=True))

    # =====================================================
    # DIRETOR / COORDENADOR
    # =====================================================
    else:

        base = Chamada.objects.filter(escola=user.escola)

        turmas = Turma.objects.filter(escola=user.escola).order_by("nome")

        disciplinas = Disciplina.objects.filter(escola=user.escola).order_by("nome")

    # =====================================================
    # DATAS DISPONÍVEIS
    # =====================================================
    datas_chamadas = (
        Chamada.objects.filter(escola=user.escola)
        .values_list(
            "data",
            flat=True,
        )
        .distinct()
        .order_by("-data")
    )

    # =====================================================
    # SEM FILTROS -> MOSTRA HOJE
    # =====================================================
    if sem_filtros:
        base = base.filter(data=hoje)

        filtro_data = hoje_str

    # =====================================================
    # FILTRO DATA
    # =====================================================
    if filtro_data:
        try:
            data_convertida = datetime.strptime(
                filtro_data,
                "%Y-%m-%d",
            ).date()

            base = base.filter(data=data_convertida)

        except ValueError:
            pass

    # =====================================================
    # FILTRO TURMA
    # =====================================================
    if filtro_turma:
        base = base.filter(turma_id=filtro_turma)

    # =====================================================
    # FILTRO DISCIPLINA
    # =====================================================
    if filtro_disciplina:
        base = base.filter(disciplina_id=filtro_disciplina)

    # =====================================================
    # QUERY FINAL
    # =====================================================
    chamadas_queryset = (
        base.select_related(
            "turma",
            "disciplina",
            "professor",
            "diario",
        )
        .distinct()
        .order_by(
            "-data",
            "turma__nome",
            "disciplina__nome",
        )
    )

    # =====================================================
    # PAGINAÇÃO
    # =====================================================
    paginator = Paginator(
        chamadas_queryset,
        20,
    )

    pagina = request.GET.get("page")

    chamadas = paginator.get_page(pagina)

    # =====================================================
    # RENDER
    # =====================================================
    return render(
        request,
        "pages/chamada/listar_chamadas.html",
        {
            "chamadas": chamadas,
            "turmas": turmas,
            "disciplinas": disciplinas,
            "data_hoje": hoje_str,
            "filtro_data": filtro_data or "",
            "filtro_turma": filtro_turma or "",
            "filtro_disciplina": filtro_disciplina or "",
            "datas_chamadas": datas_chamadas,
        },
    )


# ======================================================
# 5) DETALHE DA CHAMADA
# ======================================================
@login_required
def detalhe_chamada(request, chamada_id):

    acesso = get_professor_or_gestor(request.user)

    if acesso == "bloqueado":
        return render(
            request,
            "errors/403.html",
            status=403,
        )

    chamada = get_object_or_404(
        Chamada.objects.select_related(
            "turma",
            "disciplina",
            "professor",
            "diario",  # mantemos apenas para compatibilidade
        ),
        id=chamada_id,
        escola=request.escola,
    )

    presencas = (
        Presenca.objects.filter(chamada=chamada)
        .select_related("aluno")
        .order_by("aluno__nome")
    )

    return render(
        request,
        "pages/chamada/detalhe_chamada.html",
        {
            "chamada": chamada,
            "diario": chamada.diario,  # pode ser None
            "presencas": presencas,
        },
    )


# ======================================================
# 6) PDF DA CHAMADA
# ======================================================
@login_required
def pdf_chamada(request, chamada_id):

    acesso = get_professor_or_gestor(request.user)

    if acesso == "bloqueado":
        return render(request, "errors/403.html", status=403)

    chamada = get_object_or_404(
        Chamada.objects.select_related(
            "turma",
            "disciplina",
            "professor",
            "escola",
        ),
        id=chamada_id,
        escola=request.escola,
    )

    data = chamada.data
    turma = chamada.turma
    disciplina = chamada.disciplina
    professor = chamada.professor

    presencas = (
        Presenca.objects.filter(chamada=chamada)
        .select_related("aluno")
        .order_by("aluno__nome")
    )

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    # =====================================================
    # CABEÇALHO
    # =====================================================
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, 28 * cm, "Registro de Chamada")

    pdf.setFont("Helvetica", 12)

    pdf.drawString(
        2 * cm,
        26.8 * cm,
        f"Data: {data.strftime('%d/%m/%Y') if data else '---'}",
    )

    pdf.drawString(
        2 * cm,
        26.2 * cm,
        f"Turma: {turma.nome if turma else '---'}",
    )

    pdf.drawString(
        2 * cm,
        25.6 * cm,
        f"Disciplina: {disciplina.nome if disciplina else '---'}",
    )

    pdf.drawString(
        2 * cm,
        25.0 * cm,
        f"Professor: {professor.nome if professor else '---'}",
    )

    # =====================================================
    # TABELA
    # =====================================================
    y = 23.5 * cm

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, y, "Aluno")
    pdf.drawString(11 * cm, y, "Status")
    pdf.drawString(14 * cm, y, "Observação")

    pdf.setFont("Helvetica", 11)
    y -= 0.7 * cm

    for p in presencas:

        status = getattr(p, "status", None)
        presente = getattr(p, "presente", None)

        # Compatibilidade com registros antigos
        if not status:
            status = "P" if presente else "F"

        if status == "P":
            marca = "✔"
        elif status == "J":
            marca = "J"
        else:
            marca = "✘"

        observacao = getattr(p, "observacao", "") or ""

        pdf.drawString(2 * cm, y, p.aluno.nome[:35])
        pdf.drawString(11 * cm, y, marca)
        pdf.drawString(14 * cm, y, observacao[:25])

        y -= 0.6 * cm

        if y < 2 * cm:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = 28 * cm

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return HttpResponse(
        buffer,
        content_type="application/pdf",
    )


# ======================================================
# 7) EDITAR CHAMADA
# ======================================================
@login_required
def editar_chamada(request, chamada_id):

    acesso = get_professor_or_gestor(request.user)
    if acesso == "bloqueado":
        return render(request, "errors/403.html", status=403)

    chamada = get_object_or_404(Chamada, id=chamada_id, turma__escola=request.escola)

    presencas = (
        Presenca.objects.filter(chamada=chamada)
        .select_related("aluno")
        .order_by("aluno__nome")
    )

    return render(
        request,
        "pages/chamada/editar_chamada.html",
        {"chamada": chamada, "presencas": presencas},
    )


# ======================================================
# 8) ATUALIZAR CHAMADA
# ======================================================
@login_required
def atualizar_chamada(request, chamada_id):

    acesso = get_professor_or_gestor(request.user)

    if acesso == "bloqueado":
        return JsonResponse(
            {
                "status": "erro",
                "mensagem": "Acesso negado.",
            },
            status=403,
        )

    if request.method != "POST":
        return JsonResponse(
            {
                "status": "erro",
                "mensagem": "Método inválido",
            },
            status=405,
        )

    try:
        data = json.loads(request.body)

    except Exception:
        return JsonResponse(
            {
                "status": "erro",
                "mensagem": "JSON inválido",
            },
            status=400,
        )

    lista = data.get("lista", [])

    chamada = get_object_or_404(
        Chamada,
        id=chamada_id,
        escola=request.escola,
    )

    erros = []

    try:
        with transaction.atomic():

            for item in lista:

                aluno_id = item.get("aluno_id")

                status = (item.get("status") or "").strip().upper()

                # Compatibilidade com estrutura antiga
                if status not in ("P", "F", "J"):
                    presente_bool = bool(item.get("presente", False))
                    status = "P" if presente_bool else "F"

                presente = status == "P"

                observacao = (item.get("observacao") or "").strip()

                try:
                    aluno = Aluno.objects.get(
                        id=aluno_id,
                        escola=request.escola,
                    )

                except Aluno.DoesNotExist:
                    erros.append(
                        {
                            "aluno_id": aluno_id,
                            "mensagem": "Aluno não encontrado.",
                        }
                    )
                    continue

                Presenca.objects.update_or_create(
                    chamada=chamada,
                    aluno=aluno,
                    defaults={
                        "status": status,
                        "presente": presente,
                        "observacao": observacao,
                    },
                )

            # Atualiza auditoria
            chamada.criado_por = request.user
            chamada.save(
                update_fields=[
                    "criado_por",
                    "atualizado_em",
                ]
            )

    except Exception as e:
        return JsonResponse(
            {
                "status": "erro",
                "mensagem": "Falha ao atualizar a chamada.",
                "detalhe": str(e),
            },
            status=400,
        )

    if erros:
        return JsonResponse(
            {
                "status": "parcial",
                "erros": erros,
            }
        )

    return JsonResponse(
        {
            "status": "sucesso",
            "mensagem": "Chamada atualizada com sucesso.",
        }
    )


def relatorio_chamadas(request):
    hoje = timezone.now().date()

    mes = request.GET.get("mes")
    ano = request.GET.get("ano") or hoje.year
    turma_id = request.GET.get("turma")
    disciplina_id = request.GET.get("disciplina")

    # ===============================
    # BASE QUERYSET (OTIMIZADO)
    # ===============================
    chamadas = (
        Chamada.objects.select_related(
            "diario",
            "diario__turma",
            "diario__disciplina",
            "diario__professor",
        )
        .annotate(
            presentes=Count("presenca", filter=Q(presenca__presente=True)),
            ausentes=Count("presenca", filter=Q(presenca__presente=False)),
        )
        .order_by(
            "-diario__data_ministrada",
            "diario__hora_inicio",
        )
    )

    # ===============================
    # FILTROS
    # ===============================
    if ano:
        chamadas = chamadas.filter(diario__data_ministrada__year=ano)

    if mes:
        chamadas = chamadas.filter(diario__data_ministrada__month=mes)

    if turma_id:
        chamadas = chamadas.filter(diario__turma_id=turma_id)

    if disciplina_id:
        chamadas = chamadas.filter(diario__disciplina_id=disciplina_id)

    # ===============================
    # DADOS AUXILIARES (FILTROS)
    # ===============================
    turmas = Turma.objects.all().order_by("nome")
    disciplinas = Disciplina.objects.all().order_by("nome")

    meses = [
        {"valor": 1, "nome": "Janeiro"},
        {"valor": 2, "nome": "Fevereiro"},
        {"valor": 3, "nome": "Março"},
        {"valor": 4, "nome": "Abril"},
        {"valor": 5, "nome": "Maio"},
        {"valor": 6, "nome": "Junho"},
        {"valor": 7, "nome": "Julho"},
        {"valor": 8, "nome": "Agosto"},
        {"valor": 9, "nome": "Setembro"},
        {"valor": 10, "nome": "Outubro"},
        {"valor": 11, "nome": "Novembro"},
        {"valor": 12, "nome": "Dezembro"},
    ]

    context = {
        "chamadas": chamadas,
        "turmas": turmas,
        "disciplinas": disciplinas,
        "meses": meses,
        "ano_atual": hoje.year,
    }

    return render(request, "pages/chamada/relatorio_chamadas.html", context)


def relatorio_chamadas_pdf(request):
    hoje = timezone.now().date()

    mes = int(request.GET.get("mes", hoje.month))
    ano = int(request.GET.get("ano", hoje.year))

    chamadas = (
        Chamada.objects.select_related(
            "diario",
            "diario__turma",
            "diario__disciplina",
            "diario__professor",
            "diario__escola",
        )
        .filter(
            diario__data_ministrada__year=ano,
            diario__data_ministrada__month=mes,
        )
        .annotate(
            presentes=Count("presenca", filter=Q(presenca__presente=True)),
            ausentes=Count("presenca", filter=Q(presenca__presente=False)),
        )
        .order_by("diario__data_ministrada")
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="relatorio_chamadas_{mes}_{ano}.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    elementos = []

    escola = chamadas.first().diario.escola if chamadas.exists() else None

    # ===============================
    # CABEÇALHO
    # ===============================
    elementos.append(Paragraph("<b>RELATÓRIO MENSAL DE CHAMADAS</b>", styles["Title"]))
    elementos.append(Spacer(1, 12))

    if escola:
        elementos.append(Paragraph(f"<b>Escola:</b> {escola.nome}", styles["Normal"]))

    elementos.append(
        Paragraph(
            f"<b>Período:</b> {mes:02d}/{ano}",
            styles["Normal"],
        )
    )
    elementos.append(Spacer(1, 20))

    # ===============================
    # TABELA
    # ===============================
    dados = [
        [
            "Data",
            "Turma",
            "Disciplina",
            "Professor",
            "Presentes",
            "Ausentes",
        ]
    ]

    total_presentes = 0
    total_ausentes = 0

    for chamada in chamadas:
        dados.append(
            [
                chamada.diario.data_ministrada.strftime("%d/%m/%Y"),
                chamada.diario.turma.nome,
                chamada.diario.disciplina.nome,
                chamada.diario.professor.nome if chamada.diario.professor else "-",
                chamada.presentes,
                chamada.ausentes,
            ]
        )
        total_presentes += chamada.presentes
        total_ausentes += chamada.ausentes

    # Linha de totais
    dados.append(
        [
            "",
            "",
            "",
            "TOTAL",
            total_presentes,
            total_ausentes,
        ]
    )

    tabela = Table(dados, repeatRows=1)

    tabela.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
                ("ALIGN", (4, 1), (-1, -1), "CENTER"),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONT", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )

    elementos.append(tabela)

    doc.build(elementos)
    return response


@login_required
def resumo_mensal_turma_professor(request):
    hoje = timezone.now().date()

    mes = int(request.GET.get("mes", hoje.month))
    ano = int(request.GET.get("ano", hoje.year))

    # =====================================
    # BASE
    # =====================================

    resumo = list(
        Chamada.objects.filter(
            data__year=ano,
            data__month=mes,
        )
        .select_related(
            "turma",
            "professor",
        )
        .values(
            "turma__id",
            "turma__nome",
            "professor__id",
            "professor__nome",
        )
        .annotate(
            total_aulas=Count(
                "id",
                distinct=True,
            ),
            total_presentes=Count(
                "presencas",
                filter=Q(presencas__presente=True),
            ),
            total_ausentes=Count(
                "presencas",
                filter=Q(presencas__presente=False),
            ),
        )
        .order_by(
            "turma__nome",
            "professor__nome",
        )
    )

    # =====================================
    # PAGINAÇÃO
    # =====================================

    paginator = Paginator(resumo, 25)

    page_number = request.GET.get("page")

    resumo = paginator.get_page(page_number)

    pagina_atual = resumo.number

    inicio = max(pagina_atual - 2, 1)

    fim = min(
        pagina_atual + 2,
        paginator.num_pages,
    )

    page_range = range(inicio, fim + 1)

    # =====================================
    # AJUSTES
    # =====================================

    for item in resumo:

        total = item["total_presentes"] + item["total_ausentes"]

        if total:

            item["percentual"] = round(
                item["total_presentes"] * 100 / total,
                1,
            )

        else:

            item["percentual"] = 0

    # =====================================
    # DASHBOARD
    # =====================================

    total_turmas = len({item["turma__id"] for item in resumo})

    total_professores = len(
        {item["professor__id"] for item in resumo if item["professor__id"]}
    )

    total_aulas = sum(item["total_aulas"] for item in resumo)

    total_presentes = sum(item["total_presentes"] for item in resumo)

    total_ausentes = sum(item["total_ausentes"] for item in resumo)

    media_presenca = (
        round(
            total_presentes * 100 / (total_presentes + total_ausentes),
            1,
        )
        if (total_presentes + total_ausentes)
        else 0
    )

    # =====================================
    # MESES
    # =====================================

    meses = [
        {"valor": 1, "nome": "Janeiro"},
        {"valor": 2, "nome": "Fevereiro"},
        {"valor": 3, "nome": "Março"},
        {"valor": 4, "nome": "Abril"},
        {"valor": 5, "nome": "Maio"},
        {"valor": 6, "nome": "Junho"},
        {"valor": 7, "nome": "Julho"},
        {"valor": 8, "nome": "Agosto"},
        {"valor": 9, "nome": "Setembro"},
        {"valor": 10, "nome": "Outubro"},
        {"valor": 11, "nome": "Novembro"},
        {"valor": 12, "nome": "Dezembro"},
    ]

    # =====================================
    # CONTEXT
    # =====================================

    context = {
        "resumo": resumo,
        "meses": meses,
        "mes_atual": mes,
        "ano_atual": ano,
        "total_turmas": total_turmas,
        "total_professores": total_professores,
        "total_aulas": total_aulas,
        "total_presentes": total_presentes,
        "total_ausentes": total_ausentes,
        "media_presenca": media_presenca,
        "page_range": page_range,
    }

    return render(
        request,
        "pages/chamada/resumo_mensal_turma_professor.html",
        context,
    )


@login_required
def export_resumo_mensal_csv(request):
    hoje = timezone.now().date()

    mes = int(request.GET.get("mes", hoje.month))
    ano = int(request.GET.get("ano", hoje.year))

    resumo = (
        Chamada.objects.filter(
            data__year=ano,
            data__month=mes,
        )
        .select_related(
            "turma",
            "professor",
        )
        .values(
            "turma__nome",
            "professor__nome",
        )
        .annotate(
            total_aulas=Count(
                "id",
                distinct=True,
            ),
            total_presentes=Count(
                "presencas",
                filter=Q(presencas__presente=True),
            ),
            total_ausentes=Count(
                "presencas",
                filter=Q(presencas__presente=False),
            ),
        )
        .order_by(
            "turma__nome",
            "professor__nome",
        )
    )

    response = HttpResponse(content_type="text/csv; charset=utf-8")

    response["Content-Disposition"] = (
        f'attachment; filename="painel_gerencial_{mes:02d}_{ano}.csv"'
    )

    # UTF-8 BOM para abrir corretamente no Excel
    response.write("\ufeff")

    writer = csv.writer(response)

    writer.writerow(
        [
            "Turma",
            "Professor",
            "Aulas",
            "Presenças",
            "Faltas",
            "Frequência (%)",
        ]
    )

    for item in resumo:

        total = item["total_presentes"] + item["total_ausentes"]

        percentual = (
            round(
                item["total_presentes"] * 100 / total,
                1,
            )
            if total
            else 0
        )

        writer.writerow(
            [
                item["turma__nome"],
                item["professor__nome"] or "-",
                item["total_aulas"],
                item["total_presentes"],
                item["total_ausentes"],
                percentual,
            ]
        )

    return response


@login_required
def export_resumo_mensal_excel(request):
    hoje = timezone.now().date()

    mes = int(request.GET.get("mes", hoje.month))
    ano = int(request.GET.get("ano", hoje.year))

    resumo = list(
        Chamada.objects.filter(
            data__year=ano,
            data__month=mes,
        )
        .select_related(
            "turma",
            "professor",
        )
        .values(
            "turma__nome",
            "professor__nome",
        )
        .annotate(
            total_aulas=Count(
                "id",
                distinct=True,
            ),
            total_presentes=Count(
                "presencas",
                filter=Q(presencas__presente=True),
            ),
            total_ausentes=Count(
                "presencas",
                filter=Q(presencas__presente=False),
            ),
        )
        .order_by(
            "turma__nome",
            "professor__nome",
        )
    )

    total_turmas = len({item["turma__nome"] for item in resumo})

    total_professores = len(
        {item["professor__nome"] for item in resumo if item["professor__nome"]}
    )

    total_aulas = sum(item["total_aulas"] for item in resumo)

    total_presentes = sum(item["total_presentes"] for item in resumo)

    total_ausentes = sum(item["total_ausentes"] for item in resumo)

    media_presenca = (
        round(
            total_presentes * 100 / (total_presentes + total_ausentes),
            1,
        )
        if (total_presentes + total_ausentes)
        else 0
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Painel Gerencial"

    azul = PatternFill("solid", fgColor="2563EB")
    cinza = PatternFill("solid", fgColor="F3F4F6")
    verde = PatternFill("solid", fgColor="22C55E")
    amarelo = PatternFill("solid", fgColor="F59E0B")
    vermelho = PatternFill("solid", fgColor="EF4444")

    titulo = Font(
        bold=True,
        color="FFFFFF",
        size=18,
    )

    cabecalho = Font(
        bold=True,
        color="FFFFFF",
    )

    bold = Font(bold=True)

    center = Alignment(
        horizontal="center",
        vertical="center",
    )

    thin = Side(
        border_style="thin",
        color="DDDDDD",
    )

    border = Border(
        left=thin,
        right=thin,
        top=thin,
        bottom=thin,
    )

    # ==========================
    # CABEÇALHO
    # ==========================

    ws.merge_cells("A1:G1")

    ws["A1"] = "PAINEL GERENCIAL DE CHAMADAS"
    ws["A1"].fill = azul
    ws["A1"].font = titulo
    ws["A1"].alignment = center

    ws["A3"] = "Período"
    ws["B3"] = f"{mes:02d}/{ano}"

    ws["A4"] = "Turmas"
    ws["B4"] = total_turmas

    ws["A5"] = "Professores"
    ws["B5"] = total_professores

    ws["A6"] = "Aulas"
    ws["B6"] = total_aulas

    ws["A7"] = "Presenças"
    ws["B7"] = total_presentes

    ws["A8"] = "Faltas"
    ws["B8"] = total_ausentes

    ws["A9"] = "Frequência Média"
    ws["B9"] = f"{media_presenca}%"

    for linha in range(3, 10):
        ws[f"A{linha}"].font = bold

    # ==========================
    # TABELA
    # ==========================

    headers = [
        "Turma",
        "Professor",
        "Aulas",
        "Presenças",
        "Faltas",
        "Frequência (%)",
    ]

    linha_inicio = 11

    for col, texto in enumerate(headers, start=1):

        cell = ws.cell(
            row=linha_inicio,
            column=col,
            value=texto,
        )

        cell.fill = azul
        cell.font = cabecalho
        cell.alignment = center
        cell.border = border

    linha = linha_inicio + 1

    for item in resumo:

        total = item["total_presentes"] + item["total_ausentes"]

        percentual = (
            round(
                item["total_presentes"] * 100 / total,
                1,
            )
            if total
            else 0
        )

        dados = [
            item["turma__nome"],
            item["professor__nome"] or "-",
            item["total_aulas"],
            item["total_presentes"],
            item["total_ausentes"],
            percentual,
        ]

        for col, valor in enumerate(dados, start=1):

            cell = ws.cell(
                row=linha,
                column=col,
                value=valor,
            )

            cell.border = border

            if col >= 3:
                cell.alignment = center

        if percentual >= 75:
            ws.cell(row=linha, column=6).fill = verde
        elif percentual >= 50:
            ws.cell(row=linha, column=6).fill = amarelo
        else:
            ws.cell(row=linha, column=6).fill = vermelho

        if linha % 2 == 0:
            for col in range(1, 7):
                if col != 6:
                    ws.cell(row=linha, column=col).fill = cinza

        linha += 1

    ws.freeze_panes = "A12"
    ws.auto_filter.ref = f"A11:F{linha-1}"

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 18

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="painel_gerencial_{mes:02d}_{ano}.xlsx"'
    )

    wb.save(response)

    return response


@login_required
def relatorio_anual_chamadas(request):

    acesso = get_professor_or_gestor(request.user)

    if acesso == "bloqueado":
        return render(request, "errors/403.html", status=403)

    ano = request.GET.get("ano")

    if not ano:
        ano = datetime.now().year
    else:
        ano = int(ano)

    resumo = (
        Chamada.objects.filter(
            escola=request.escola,
            data__year=ano,
        )
        .values(
            "turma__nome",
            "disciplina__nome",
            "professor__nome",
        )
        .annotate(
            total_aulas=Count("id", distinct=True),
            total_presentes=Count(
                "presencas",
                filter=Q(presencas__presente=True),
                distinct=True,
            ),
            total_ausentes=Count(
                "presencas",
                filter=Q(presencas__presente=False),
                distinct=True,
            ),
        )
        .order_by(
            "turma__nome",
            "disciplina__nome",
            "professor__nome",
        )
    )

    return render(
        request,
        "pages/chamada/relatorio_anual_chamadas.html",
        {
            "resumo": resumo,
            "ano": ano,
        },
    )


@login_required
def relatorio_anual_chamadas_pdf(request):

    acesso = get_professor_or_gestor(request.user)

    if acesso == "bloqueado":
        return render(request, "errors/403.html", status=403)

    ano = request.GET.get("ano")

    if not ano:
        return HttpResponse("Ano não informado.", status=400)

    ano = int(ano)

    resumo = (
        Presenca.objects.filter(
            chamada__data__year=ano,
            chamada__escola=request.escola,
        )
        .values(
            "chamada__turma__nome",
            "chamada__disciplina__nome",
            "chamada__professor__nome",
        )
        .annotate(
            total_aulas=Count("chamada", distinct=True),
            total_presentes=Count(
                "id",
                filter=Q(presente=True),
            ),
            total_ausentes=Count(
                "id",
                filter=Q(presente=False),
            ),
        )
        .order_by(
            "chamada__turma__nome",
            "chamada__disciplina__nome",
            "chamada__professor__nome",
        )
    )

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 2 * cm

    # TÍTULO
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, y, "Relatório Anual de Chamadas")
    y -= 0.8 * cm

    pdf.setFont("Helvetica", 12)
    pdf.drawString(2 * cm, y, f"Ano: {ano}")
    y -= 0.5 * cm

    pdf.drawString(2 * cm, y, f"Escola: {request.escola.nome}")
    y -= 1.2 * cm

    # CABEÇALHO
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(2 * cm, y, "Turma")
    pdf.drawString(6 * cm, y, "Disciplina")
    pdf.drawString(10 * cm, y, "Professor")
    pdf.drawString(14 * cm, y, "Aulas")
    pdf.drawString(15.5 * cm, y, "P")
    pdf.drawString(17 * cm, y, "F")

    y -= 0.4 * cm
    pdf.line(2 * cm, y, 19 * cm, y)
    y -= 0.5 * cm

    pdf.setFont("Helvetica", 10)

    for r in resumo:

        if y < 2 * cm:
            pdf.showPage()
            y = height - 2 * cm

            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(2 * cm, y, "Turma")
            pdf.drawString(6 * cm, y, "Disciplina")
            pdf.drawString(10 * cm, y, "Professor")
            pdf.drawString(14 * cm, y, "Aulas")
            pdf.drawString(15.5 * cm, y, "P")
            pdf.drawString(17 * cm, y, "F")

            y -= 0.4 * cm
            pdf.line(2 * cm, y, 19 * cm, y)
            y -= 0.5 * cm

            pdf.setFont("Helvetica", 10)

        pdf.drawString(2 * cm, y, r["chamada__turma__nome"][:20])
        pdf.drawString(6 * cm, y, r["chamada__disciplina__nome"][:20])
        pdf.drawString(
            10 * cm,
            y,
            (r["chamada__professor__nome"] or "—")[:18],
        )
        pdf.drawRightString(15 * cm, y, str(r["total_aulas"]))
        pdf.drawRightString(16.5 * cm, y, str(r["total_presentes"]))
        pdf.drawRightString(18 * cm, y, str(r["total_ausentes"]))

        y -= 0.45 * cm

    pdf.save()

    buffer.seek(0)

    return HttpResponse(
        buffer,
        content_type="application/pdf",
    )


@login_required
def relatorio_anual_chamadas_excel(request):

    acesso = get_professor_or_gestor(request.user)

    if acesso == "bloqueado":
        return JsonResponse({"erro": "Acesso negado"}, status=403)

    ano = request.GET.get("ano")

    if not ano:
        return JsonResponse({"erro": "Ano não informado"}, status=400)

    ano = int(ano)

    resumo = (
        Presenca.objects.filter(
            chamada__data__year=ano,
            chamada__escola=request.escola,
        )
        .values(
            "chamada__turma__nome",
            "chamada__disciplina__nome",
            "chamada__professor__nome",
        )
        .annotate(
            total_aulas=Count("chamada", distinct=True),
            total_presentes=Count(
                "id",
                filter=Q(presente=True),
            ),
            total_ausentes=Count(
                "id",
                filter=Q(presente=False),
            ),
        )
        .order_by(
            "chamada__turma__nome",
            "chamada__disciplina__nome",
            "chamada__professor__nome",
        )
    )

    wb = Workbook()
    ws = wb.active
    ws.title = f"Chamadas {ano}"

    headers = [
        "Turma",
        "Disciplina",
        "Professor",
        "Total de Aulas",
        "Presentes",
        "Ausentes",
    ]

    ws.append(headers)

    from openpyxl.styles import Font, Alignment

    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    for r in resumo:
        ws.append(
            [
                r["chamada__turma__nome"],
                r["chamada__disciplina__nome"],
                r["chamada__professor__nome"] or "-",
                r["total_aulas"],
                r["total_presentes"],
                r["total_ausentes"],
            ]
        )

    # Autoajuste das colunas
    for col in ws.columns:
        max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_length + 3

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="relatorio_chamadas_{ano}.xlsx"'
    )

    wb.save(response)

    return response
