import json
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction

from home.models import (
    RelatorioIndividual,
    Aluno,
    Turma,
    Docente,
    TurmaDisciplina,
)

MAX_TEXTO = 3000  # limite seguro (pode ajustar)


@login_required
def relatorio_individual_view(request):
    """
    Tela principal do Relatório Individual
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
        "pages/relatorio_individual.html",
        {
            "turmas": turmas,
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
            return JsonResponse({"status": "erro", "mensagem": "Professor inválido"}, status=403)

        permitido = TurmaDisciplina.objects.filter(
            professor=professor,
            turma=turma,
            turma__escola=escola,
        ).exists()

        if not permitido:
            return JsonResponse(
                {"status": "erro", "mensagem": "Turma não permitida para este professor"},
                status=403
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
            {"erro": "Parâmetros obrigatórios: aluno, turma, ano_letivo"},
            status=400
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
            return JsonResponse({"erro": "Turma não permitida para este professor"}, status=403)

    registros = (
        RelatorioIndividual.objects
        .filter(
            aluno=aluno,
            turma=turma,
            ano_letivo=int(ano_letivo),
            escola=escola,
        )
        .values("bimestre", "observacoes")
    )

    resposta = {1: "", 2: "", 3: "", 4: ""}
    for r in registros:
        resposta[int(r["bimestre"])] = r["observacoes"] or ""

    return JsonResponse(resposta)