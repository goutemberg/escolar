import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from home.decorators import role_required
from home.models import Turma, Avaliacao, Nota, AnoLetivo
from home.utils import get_ano_ativo, get_escola_ativa


@login_required
@role_required(["diretor", "coordenador"])
def fechamento_ano_letivo(request):

    ano = get_ano_ativo()
    escola = get_escola_ativa(request)

    total_turmas = 0
    total_avaliacoes = 0
    total_notas = 0

    if ano and escola:

        total_turmas = Turma.objects.filter(
            escola=escola,
            ano_letivo=ano,
        ).count()

        total_avaliacoes = Avaliacao.objects.filter(
            escola=escola,
            turma__ano_letivo=ano,
        ).count()

        total_notas = Nota.objects.filter(
            escola=escola,
            avaliacao__turma__ano_letivo=ano,
        ).count()

    context = {
        "ano": ano,
        "total_turmas": total_turmas,
        "total_avaliacoes": total_avaliacoes,
        "total_notas": total_notas,
    }

    return render(
        request,
        "pages/fechar_ano_letivo.html",
        context,
    )


@login_required
@role_required(["diretor", "coordenador"])
@require_POST
def fechar_ano_letivo(request):

    escola = get_escola_ativa(request)

    if not escola:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Não foi possível identificar a escola ativa.",
            },
            status=400,
        )

    ano = get_ano_ativo()

    if not ano:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Não existe um ano letivo ativo.",
            },
            status=400,
        )

    try:
        dados = json.loads(request.body)
        ano_id = dados.get("ano_id")
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Dados da requisição inválidos.",
            },
            status=400,
        )

    if not ano_id:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Ano letivo não informado.",
            },
            status=400,
        )

    try:
        ano_id = int(ano_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Ano letivo inválido.",
            },
            status=400,
        )

    if ano.id != ano_id:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "O ano letivo informado não corresponde ao ano ativo.",
            },
            status=400,
        )

    if ano.encerrado:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Este ano letivo já está encerrado.",
            },
            status=400,
        )

    # ==========================================
    # FECHAMENTO EFETIVO DO ANO LETIVO
    # ==========================================

    ano.encerrado = True
    ano.ativo = False
    ano.data_fim = timezone.now().date()

    ano.save(
        update_fields=[
            "encerrado",
            "ativo",
            "data_fim",
        ]
    )

    return JsonResponse(
        {
            "success": True,
            "mensagem": f"Ano letivo {ano.ano} encerrado com sucesso.",
        }
    )


@login_required
@role_required(["diretor", "coordenador"])
@require_POST
def abrir_ano_letivo(request):

    escola = get_escola_ativa(request)

    if not escola:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Não foi possível identificar a escola ativa.",
            },
            status=400,
        )

    # ==========================================
    # NÃO PODE EXISTIR ANO ATIVO
    # ==========================================

    ano_ativo = get_ano_ativo()

    if ano_ativo:
        return JsonResponse(
            {
                "success": False,
                "mensagem": (
                    f"O ano letivo {ano_ativo.ano} ainda está ativo. "
                    "É necessário encerrá-lo antes de abrir um novo ano."
                ),
            },
            status=400,
        )

    # ==========================================
    # LEITURA DOS DADOS
    # ==========================================

    try:
        dados = json.loads(request.body)
        novo_ano = dados.get("ano")
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Dados da requisição inválidos.",
            },
            status=400,
        )

    if not novo_ano:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Novo ano letivo não informado.",
            },
            status=400,
        )

    # ==========================================
    # VALIDAÇÃO DO ANO
    # ==========================================

    try:
        novo_ano = int(novo_ano)
    except (TypeError, ValueError):
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Novo ano letivo inválido.",
            },
            status=400,
        )

    if novo_ano < 2000 or novo_ano > 2100:
        return JsonResponse(
            {
                "success": False,
                "mensagem": "Informe um ano letivo entre 2000 e 2100.",
            },
            status=400,
        )

    # ==========================================
    # NÃO PERMITIR ANO DUPLICADO
    # ==========================================

    if AnoLetivo.objects.filter(ano=novo_ano).exists():
        return JsonResponse(
            {
                "success": False,
                "mensagem": (f"O ano letivo {novo_ano} já existe no sistema."),
            },
            status=400,
        )

    # ==========================================
    # ABERTURA EFETIVA DO NOVO ANO
    # ==========================================

    ano = AnoLetivo.objects.create(
        ano=novo_ano,
        ativo=True,
        encerrado=False,
        data_inicio=timezone.now().date(),
        data_fim=None,
    )

    return JsonResponse(
        {
            "success": True,
            "mensagem": (f"Ano letivo {ano.ano} aberto com sucesso."),
            "ano": ano.ano,
            "data_inicio": ano.data_inicio.isoformat(),
        }
    )
