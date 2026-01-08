import json
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction

from home.models import (
    RegistroPedagogico,
    Aluno,
    Turma,
)

MAX_TEXTO = 3000  # limite seguro (pode ajustar)

@login_required
def registro_pedagogico_view(request):
    """
    Tela principal do Registro Pedagógico
    """
    usuario = request.user
    escola = usuario.escola

    turmas = Turma.objects.filter(escola=escola)

    return render(
        request,
        "pages/registro_pedagogico.html",
        {
            "turmas": turmas,
            "ano_atual": date.today().year,
        },
    )

@login_required
@require_POST
@transaction.atomic
def salvar_registro_pedagogico(request):
    usuario = request.user
    escola = usuario.escola

    # 🔒 Blindagem por role
    if usuario.role not in ["professor", "coordenador", "diretor"]:
        return JsonResponse({"status": "erro", "mensagem": "Acesso negado"}, status=403)

    # 🔒 Blindagem JSON
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

    # 🔒 Campos obrigatórios
    if not all([aluno_id, turma_id, ano_letivo, registros]):
        return JsonResponse(
            {"status": "erro", "mensagem": "Dados obrigatórios ausentes"},
            status=400,
        )

    # 🔒 Tipos básicos
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

    # 🔒 Aluno e turma SEMPRE da mesma escola
    try:
        aluno = Aluno.objects.get(id=aluno_id, escola=escola)
        turma = Turma.objects.get(id=turma_id, escola=escola)
    except (Aluno.DoesNotExist, Turma.DoesNotExist):
        return JsonResponse(
            {"status": "erro", "mensagem": "Aluno ou turma inválidos"},
            status=404,
        )

    # 🔒 Transação atômica
    with transaction.atomic():
        for trimestre, texto in registros.items():

            # 🔒 Trimestre válido
            try:
                trimestre = int(trimestre)
            except (TypeError, ValueError):
                continue  # ignora lixo silenciosamente

            if trimestre not in [1, 2, 3, 4]:
                continue  # ignora trimestre inválido

            # 🔒 Texto seguro
            if texto is None:
                texto = ""

            if not isinstance(texto, str):
                texto = str(texto)

            texto = texto.strip()

            if len(texto) > MAX_TEXTO:
                texto = texto[:MAX_TEXTO]

            # 🔒 Upsert controlado
            RegistroPedagogico.objects.update_or_create(
                aluno=aluno,
                turma=turma,
                ano_letivo=ano_letivo,
                trimestre=trimestre,
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
def buscar_registros_pedagogicos(request):
    usuario = request.user
    escola = usuario.escola

    # Blindagem por role
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

    registros = (
        RegistroPedagogico.objects
        .filter(
            aluno=aluno,
            turma=turma,
            ano_letivo=int(ano_letivo),
            escola=escola,
        )
        .values("trimestre", "observacoes")
    )

    # Resposta previsível (sempre 1..4)
    resposta = {1: "", 2: "", 3: "", 4: ""}
    for r in registros:
        resposta[int(r["trimestre"])] = r["observacoes"] or ""

    return JsonResponse(resposta)