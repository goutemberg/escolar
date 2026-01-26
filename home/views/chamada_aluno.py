from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, IntegrityError
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

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
)

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
        prof_obj = Docente.objects.filter(
            user=user,
            escola=user.escola
        ).first()

        if not prof_obj:
            return HttpResponseForbidden("Professor sem vínculo docente.")

        turmas_disciplinas = (
            TurmaDisciplina.objects
            .filter(
                professor=prof_obj,
                escola=user.escola
            )
            .select_related("turma", "disciplina")
        )

    # -------------------------------------------------
    # COORDENADOR / DIRETOR
    # -------------------------------------------------
    else:
        turmas_disciplinas = (
            TurmaDisciplina.objects
            .filter(escola=user.escola)
            .select_related("turma", "disciplina")
        )

    # -------------------------------------------------
    # Extrair listas sem duplicação
    # -------------------------------------------------
    turmas = sorted(
        {td.turma for td in turmas_disciplinas},
        key=lambda t: t.nome
    )

    disciplinas = sorted(
        {td.disciplina for td in turmas_disciplinas},
        key=lambda d: d.nome
    )

    return render(
        request,
        "pages/chamada/realizar_chamadas.html",
        {
            "turmas": turmas,
            "disciplinas": disciplinas,
            "data_hoje": hoje,
        }
    )

# ======================================================
# 2) API – CARREGAR ALUNOS DA TURMA
# ======================================================
@login_required
def api_carregar_alunos(request, turma_id):

    try:
        turma = Turma.objects.get(id=turma_id, escola=request.user.escola)
    except Turma.DoesNotExist:
        return JsonResponse({"erro": "Turma não encontrada."}, status=404)

    alunos = (
        turma.alunos.filter(ativo=True)
        .order_by("nome")
        .values("id", "nome")
    )

    return JsonResponse({"alunos": list(alunos)})


# ======================================================
# 3) SALVAR PRESENÇAS
# ======================================================
@csrf_exempt
@login_required
def salvar_presencas(request):

    acesso = get_professor_or_gestor(request.user)
    if acesso == "bloqueado":
        return JsonResponse(
            {"status": "erro", "mensagem": "Acesso negado."},
            status=403
        )

    if request.method != "POST":
        return JsonResponse(
            {"status": "erro", "mensagem": "Método não permitido"},
            status=405
        )

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse(
            {"status": "erro", "mensagem": "JSON inválido"},
            status=400
        )

    turma_id = data.get("turma")
    disciplina_id = data.get("disciplina")
    data_aula = data.get("data")
    lista = data.get("lista", [])

    if not turma_id or not disciplina_id or not data_aula:
        return JsonResponse(
            {"status": "erro", "mensagem": "Campos obrigatórios faltando."},
            status=400
        )

    # ===============================
    # PROFESSOR (APENAS SE NECESSÁRIO)
    # ===============================
    professor = None

    if acesso == "professor":
        professor = Docente.objects.filter(
            user=request.user,
            escola=request.user.escola
        ).first()

        if not professor:
            return JsonResponse(
                {
                    "status": "erro",
                    "mensagem": "Professor não está vinculado corretamente."
                },
                status=400
            )

    # ===============================
    # TURMA
    # ===============================
    try:
        turma = Turma.objects.get(
            id=turma_id,
            escola=request.user.escola
        )
    except Turma.DoesNotExist:
        return JsonResponse(
            {"status": "erro", "mensagem": "Turma inválida."},
            status=404
        )

    # ===============================
    # DISCIPLINA
    # ===============================
    try:
        disciplina = Disciplina.objects.get(
            id=disciplina_id,
            escola=request.user.escola
        )
    except Disciplina.DoesNotExist:
        return JsonResponse(
            {"status": "erro", "mensagem": "Disciplina inválida."},
            status=404
        )

    # ===============================
    # VALIDAÇÃO DE VÍNCULO (SÓ PROFESSOR)
    # ===============================
    if acesso == "professor":
        if not TurmaDisciplina.objects.filter(
            turma=turma,
            disciplina=disciplina,
            professor=professor
        ).exists():
            return JsonResponse(
                {
                    "status": "erro",
                    "mensagem": "Você não está vinculado a esta disciplina nesta turma."
                },
                status=403
            )

    # ===============================
    # DATA
    # ===============================
    try:
        data_aula = datetime.strptime(data_aula, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse(
            {"status": "erro", "mensagem": "Data inválida."},
            status=400
        )

    erros_alunos = []

    # ===============================
    # TRANSAÇÃO
    # ===============================
    try:
        with transaction.atomic():

            chamada, created = Chamada.objects.get_or_create(
                data=data_aula,
                turma=turma,
                disciplina=disciplina,
                defaults={
                    "professor": professor if acesso == "professor" else None,
                    "feita_por": request.user,
                }
            )

            # Atualiza dados caso já exista
            if not created:
                alterou = False

                if acesso == "professor" and chamada.professor is None:
                    chamada.professor = professor
                    alterou = True

                if chamada.feita_por != request.user:
                    chamada.feita_por = request.user
                    alterou = True

                if alterou:
                    chamada.save()

            # ===============================
            # PRESENÇAS
            # ===============================
            for item in lista:
                aluno_id = item.get("aluno_id")
                presente = item.get("presente", False)
                obs = item.get("observacao", "")

                try:
                    aluno = Aluno.objects.get(
                        id=aluno_id,
                        escola=request.user.escola
                    )
                except Aluno.DoesNotExist:
                    erros_alunos.append({
                        "aluno_id": aluno_id,
                        "mensagem": "Aluno não encontrado."
                    })
                    continue

                Presenca.objects.update_or_create(
                    chamada=chamada,
                    aluno=aluno,
                    defaults={
                        "presente": presente,
                        "observacao": obs,
                    }
                )

    except IntegrityError:
        return JsonResponse(
            {
                "status": "erro",
                "mensagem": (
                    "Já existe uma chamada registrada para esta "
                    "turma, disciplina e data."
                )
            },
            status=400
        )

    # ===============================
    # RETORNO FINAL
    # ===============================
    if erros_alunos:
        return JsonResponse(
            {"status": "parcial", "erros": erros_alunos},
            status=207
        )

    return JsonResponse(
        {
            "status": "sucesso",
            "mensagem": "Chamada salva com sucesso!"
        }
    )


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

    professor = Docente.objects.filter(user=user).first()

    # =====================================================
    # PERFIL PROFESSOR
    # =====================================================
    if professor:

        # Chamadas SOMENTE do professor
        base = Chamada.objects.filter(
            professor=professor,
            turma__escola=user.escola
        )

        # Turmas derivadas de TurmaDisciplina
        turmas = Turma.objects.filter(
            turmadisciplina__professor=professor,
            escola=user.escola
        ).distinct().order_by("nome")

        # Disciplinas derivadas de TurmaDisciplina
        disciplinas = Disciplina.objects.filter(
            turmadisciplina__professor=professor,
            escola=user.escola
        ).distinct().order_by("nome")

    # =====================================================
    # PERFIL DIRETOR / COORDENADOR
    # =====================================================
    else:
        base = Chamada.objects.filter(
            turma__escola=user.escola
        )

        turmas = Turma.objects.filter(
            escola=user.escola
        ).order_by("nome")

        disciplinas = Disciplina.objects.filter(
            escola=user.escola
        ).order_by("nome")

    # =====================================================
    # FILTROS
    # =====================================================
    if sem_filtros:
        base = base.filter(data=hoje)
        filtro_data = hoje_str

    if filtro_data:
        try:
            data_convertida = datetime.strptime(filtro_data, "%Y-%m-%d").date()
            base = base.filter(data=data_convertida)
        except ValueError:
            pass

    if filtro_turma:
        base = base.filter(turma_id=filtro_turma)

    if filtro_disciplina:
        base = base.filter(disciplina_id=filtro_disciplina)

    # =====================================================
    # QUERY FINAL
    # =====================================================
    chamadas_queryset = (
        base
        .select_related("turma", "disciplina", "professor")
        .order_by("-data", "turma__nome", "disciplina__nome")
    )

    # =====================================================
    # PAGINAÇÃO
    # =====================================================
    from django.core.paginator import Paginator
    paginator = Paginator(chamadas_queryset, 20)
    pagina = request.GET.get("page")
    chamadas = paginator.get_page(pagina)

    # =====================================================
    # RENDER
    # =====================================================
    return render(request, "pages/chamada/listar_chamadas.html", {
        "chamadas": chamadas,
        "turmas": turmas,
        "disciplinas": disciplinas,
        "data_hoje": hoje_str,
        "filtro_data": filtro_data or "",
        "filtro_turma": filtro_turma or "",
        "filtro_disciplina": filtro_disciplina or "",
    })


# ======================================================
# 5) DETALHE DA CHAMADA
# ======================================================
@login_required
def detalhe_chamada(request, chamada_id):

    acesso = get_professor_or_gestor(request.user)
    if acesso == "bloqueado":
        return render(request, "errors/403.html", status=403)

    chamada = get_object_or_404(
        Chamada,
        id=chamada_id,
        turma__escola=request.user.escola
    )

    presencas = (
        Presenca.objects.filter(chamada=chamada)
        .select_related("aluno")
        .order_by("aluno__nome")
    )

    return render(request, "pages/chamada/detalhe_chamada.html", {
        "chamada": chamada,
        "presencas": presencas
    })


# ======================================================
# 6) PDF DA CHAMADA
# ======================================================
@login_required
def pdf_chamada(request, chamada_id):

    acesso = get_professor_or_gestor(request.user)
    if acesso == "bloqueado":
        return render(request, "errors/403.html", status=403)

    chamada = get_object_or_404(
        Chamada,
        id=chamada_id,
        turma__escola=request.user.escola
    )

    presencas = (
        Presenca.objects.filter(chamada=chamada)
        .select_related("aluno")
        .order_by("aluno__nome")
    )

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, 28 * cm, "Registro de Chamada")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(2 * cm, 26.8 * cm, f"Data: {chamada.data.strftime('%d/%m/%Y')}")
    pdf.drawString(2 * cm, 26.2 * cm, f"Turma: {chamada.turma.nome}")
    pdf.drawString(2 * cm, 25.6 * cm, f"Disciplina: {chamada.disciplina.nome}")
    pdf.drawString(2 * cm, 25.0 * cm, f"Professor: {chamada.professor.nome if chamada.professor else '---'}")

    y = 23.5 * cm

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, y, "Aluno")
    pdf.drawString(11 * cm, y, "Presente")
    pdf.drawString(14 * cm, y, "Observação")

    pdf.setFont("Helvetica", 11)
    y -= 0.7 * cm

    for p in presencas:
        pdf.drawString(2 * cm, y, p.aluno.nome[:35])
        pdf.drawString(11 * cm, y, "✔" if p.presente else "✘")
        pdf.drawString(14 * cm, y, (p.observacao or "")[:20])
        y -= 0.6 * cm

        if y < 2 * cm:
            pdf.showPage()
            y = 28 * cm

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf")


# ======================================================
# 7) EDITAR CHAMADA
# ======================================================
@login_required
def editar_chamada(request, chamada_id):

    acesso = get_professor_or_gestor(request.user)
    if acesso == "bloqueado":
        return render(request, "errors/403.html", status=403)

    chamada = get_object_or_404(
        Chamada,
        id=chamada_id,
        turma__escola=request.user.escola
    )

    presencas = (
        Presenca.objects.filter(chamada=chamada)
        .select_related("aluno")
        .order_by("aluno__nome")
    )

    return render(request, "pages/chamada/editar_chamada.html", {
        "chamada": chamada,
        "presencas": presencas
    })


# ======================================================
# 8) ATUALIZAR CHAMADA
# ======================================================
@login_required
def atualizar_chamada(request, chamada_id):

    acesso = get_professor_or_gestor(request.user)
    if acesso == "bloqueado":
        return JsonResponse({"status": "erro", "mensagem": "Acesso negado."}, status=403)

    if request.method != "POST":
        return JsonResponse({"status": "erro", "mensagem": "Método inválido"}, status=405)

    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({"status": "erro", "mensagem": "JSON inválido"}, status=400)

    lista = data.get("lista", [])

    chamada = get_object_or_404(
        Chamada,
        id=chamada_id,
        turma__escola=request.user.escola
    )

    erros = []

    try:
        with transaction.atomic():

            for item in lista:
                aluno_id = item.get("aluno_id")
                presente = item.get("presente", False)
                obs = item.get("observacao", "")

                try:
                    aluno = Aluno.objects.get(id=aluno_id, escola=request.user.escola)
                except:
                    erros.append({
                        "aluno_id": aluno_id,
                        "mensagem": "Aluno não encontrado."
                    })
                    continue

                Presenca.objects.update_or_create(
                    chamada=chamada,
                    aluno=aluno,
                    defaults={
                        "presente": presente,
                        "observacao": obs,
                    }
                )

            chamada.feita_por = request.user
            chamada.save()

    except Exception:
        return JsonResponse({
            "status": "erro",
            "mensagem": "Falha ao atualizar a chamada."
        }, status=400)

    if erros:
        return JsonResponse({"status": "parcial", "erros": erros})

    return JsonResponse({"status": "sucesso", "mensagem": "Chamada atualizada com sucesso."})
