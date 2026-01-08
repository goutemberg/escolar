from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from home.models import Aluno, Turma


@login_required
@require_GET
def alunos_por_turma(request):
    usuario = request.user
    escola = usuario.escola

    if usuario.role not in ["professor", "coordenador", "diretor"]:
        return JsonResponse({"erro": "Acesso negado"}, status=403)

    turma_id = request.GET.get("turma")

    if not turma_id:
        return JsonResponse(
            {"erro": "Parâmetro 'turma' é obrigatório"},
            status=400
        )

    try:
        turma = Turma.objects.get(
            id=turma_id,
            escola=escola
        )
    except Turma.DoesNotExist:
        return JsonResponse(
            {"erro": "Turma não encontrada"},
            status=404
        )

    alunos = (
        Aluno.objects
        .filter(
            turma_principal=turma,
            escola=escola,
            ativo=True
        )
        .order_by("nome")
        .values("id", "nome")
    )

    return JsonResponse(list(alunos), safe=False)
