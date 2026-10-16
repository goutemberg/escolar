from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from home.decorators import role_required
from home.models import Aluno, Turma
from home.services.dashboard_diretor import (
    obter_dashboard_diretor,
    obter_detalhamento_aluno,
    obter_detalhamento_turma,
)
from home.utils import get_ano_ativo


@login_required
@role_required(["diretor", "coordenador"])
def dashboard_diretor(request):
    """
    Dashboard executivo do diretor.
    """

    contexto = obter_dashboard_diretor(request.user)

    return render(
        request,
        "pages/dashboard_diretor.html",
        contexto,
    )


@login_required
@role_required(["diretor", "coordenador"])
def dashboard_diretor_turma(request, turma_id):
    """
    Diagnóstico individual de uma turma.

    O diretor só pode consultar turmas:
    - da própria escola;
    - do ano letivo ativo;
    - que estejam ativas.
    """

    escola = getattr(
        request.user,
        "escola",
        None,
    )

    ano_letivo = get_ano_ativo()

    if not escola or not ano_letivo:
        return render(
            request,
            "pages/dashboard_diretor_turma.html",
            {
                "turma": None,
                "erro": ("Escola ou ano letivo " "não identificado."),
            },
        )

    turma = get_object_or_404(
        Turma.objects.select_related(
            "escola",
            "ano_letivo",
        ),
        id=turma_id,
        escola=escola,
        ano_letivo=ano_letivo,
        status="ATIVA",
    )

    contexto = obter_detalhamento_turma(
        turma,
        ano_letivo,
    )

    return render(
        request,
        "pages/dashboard_diretor_turma.html",
        contexto,
    )


@login_required
@role_required(["diretor", "coordenador"])
def dashboard_diretor_aluno(request, aluno_id):
    """
    Diagnóstico individual de um aluno.

    O aluno precisa:
    - pertencer à escola do diretor;
    - possuir matrícula ativa;
    - estar matriculado no ano letivo ativo.
    """

    escola = getattr(
        request.user,
        "escola",
        None,
    )

    ano_letivo = get_ano_ativo()

    if not escola or not ano_letivo:
        return render(
            request,
            "pages/dashboard_diretor_aluno.html",
            {
                "aluno": None,
                "erro": ("Escola ou ano letivo " "não identificado."),
            },
        )

    aluno = get_object_or_404(
        Aluno.objects.select_related(
            "escola",
        ),
        id=aluno_id,
        escola=escola,
    )

    contexto = obter_detalhamento_aluno(
        aluno,
        ano_letivo,
    )

    if contexto is None:
        return render(
            request,
            "pages/dashboard_diretor_aluno.html",
            {
                "aluno": aluno,
                "erro": (
                    "Este aluno não possui " "matrícula ativa no ano " "letivo atual."
                ),
            },
        )

    return render(
        request,
        "pages/dashboard_diretor_aluno.html",
        contexto,
    )
