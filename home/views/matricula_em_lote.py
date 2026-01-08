import json

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from home.models import Aluno, Turma


@login_required
@require_POST
def salvar_matricula_lote(request):
    """
    Salva alunos em lote (irmãos),
    reaproveitando a lógica normal de matrícula.
    """

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "erro", "mensagem": "JSON inválido"},
            status=400
        )

    dados_comuns = data.get("dados_comuns", {})
    alunos_data = data.get("alunos", [])

    if not alunos_data or len(alunos_data) < 2:
        return JsonResponse(
            {"status": "erro", "mensagem": "Informe pelo menos dois alunos"},
            status=400
        )

    escola = getattr(request.user, "escola", None)
    if not escola:
        return JsonResponse(
            {"status": "erro", "mensagem": "Usuário sem escola associada"},
            status=403
        )

    alunos_criados = []

    try:
        with transaction.atomic():

            for aluno_data in alunos_data:

                aluno = Aluno(
                    # ===== Dados individuais
                    nome=aluno_data.get("nome", "").strip(),
                    data_nascimento=aluno_data.get("data_nascimento") or None,
                    cpf=aluno_data.get("cpf", "").strip(),
                    rg=aluno_data.get("rg", "").strip(),
                    sexo=aluno_data.get("sexo", "").strip(),

                    # ===== Dados comuns
                    serie_ano=dados_comuns.get("serie_ano", "").strip(),
                    turno=dados_comuns.get("turno", "").strip(),
                    nivel_modalidade=dados_comuns.get("nivel_modalidade", "").strip(),
                    turma_id=dados_comuns.get("turma_id") or None,

                    # ===== Sistema
                    escola=escola,
                )

                # 🔑 matrícula gerada automaticamente no save()
                aluno.save()

                alunos_criados.append({
                    "id": aluno.id,
                    "nome": aluno.nome,
                    "matricula": aluno.matricula
                })

    except Exception as e:
        return JsonResponse(
            {
                "status": "erro",
                "mensagem": "Erro ao salvar matrículas",
                "detalhe": str(e)
            },
            status=500
        )

    return JsonResponse(
        {
            "status": "sucesso",
            "total": len(alunos_criados),
            "alunos": alunos_criados
        }
    )


@login_required
def registro_matricula_lote(request):
    escola = getattr(request.user, "escola", None)

    turmas = []
    if escola:
        turmas = Turma.objects.filter(escola=escola).order_by("nome")

    return render(
        request,
        "pages/registro_lote.html",
        {"turmas": turmas}
    )
