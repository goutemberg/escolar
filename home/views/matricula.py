# ============================================================
# MATRÍCULAS
# ============================================================

import json

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from home.decorators import role_required
from home.models import Aluno, Matricula, Turma
from home.utils import get_ano_ativo

# ============================================================
# LISTAGEM DE MATRÍCULAS
# ============================================================


@login_required
@role_required(["diretor", "coordenador"])
def listar_matriculas(request):

    escola = request.escola
    ano_ativo = get_ano_ativo()

    matriculas = []
    turmas = []

    if ano_ativo:

        matriculas = (
            Matricula.objects.filter(
                ano_letivo=ano_ativo,
                aluno__escola=escola,
            )
            .select_related(
                "aluno",
                "turma",
                "ano_letivo",
            )
            .order_by("aluno__nome")
        )

        turmas = Turma.objects.filter(
            escola=escola,
            ano_letivo=ano_ativo,
        ).order_by("nome")

    return render(
        request,
        "pages/listar_matriculas.html",
        {
            "ano_ativo": ano_ativo,
            "matriculas": matriculas,
            "turmas": turmas,
        },
    )


# ============================================================
# NOVA MATRÍCULA - TELA
# ============================================================


@login_required
@role_required(["diretor", "coordenador"])
def nova_matricula(request):

    escola = request.escola
    ano_ativo = get_ano_ativo()

    alunos = []
    turmas = []

    if ano_ativo:

        alunos = Aluno.objects.filter(
            escola=escola,
            ativo=True,
        ).order_by("nome")

        turmas = Turma.objects.filter(
            escola=escola,
            ano_letivo=ano_ativo,
        ).order_by("nome")

    return render(
        request,
        "pages/nova_matricula.html",
        {
            "ano_ativo": ano_ativo,
            "alunos": alunos,
            "turmas": turmas,
        },
    )


# ============================================================
# SALVAR MATRÍCULA
# ============================================================


@login_required
@role_required(["diretor", "coordenador"])
@require_POST
def salvar_matricula(request):

    escola = request.escola

    # --------------------------------------------------------
    # 1. Verificar ano letivo ativo
    # --------------------------------------------------------

    ano_ativo = get_ano_ativo()

    if not ano_ativo:

        return JsonResponse(
            {
                "success": False,
                "mensagem": (
                    "Não existe um ano letivo ativo " "para realizar a matrícula."
                ),
            },
            status=400,
        )

    # --------------------------------------------------------
    # 2. Ler JSON
    # --------------------------------------------------------

    try:

        data = json.loads(request.body or "{}")

    except (json.JSONDecodeError, TypeError):

        return JsonResponse(
            {
                "success": False,
                "mensagem": "Dados da matrícula inválidos.",
            },
            status=400,
        )

    aluno_id = data.get("aluno_id")
    turma_id = data.get("turma_id")

    # --------------------------------------------------------
    # 3. Validar aluno
    # --------------------------------------------------------

    if not aluno_id:

        return JsonResponse(
            {
                "success": False,
                "mensagem": "Aluno não informado.",
            },
            status=400,
        )

    # --------------------------------------------------------
    # 4. Buscar aluno dentro da escola
    # --------------------------------------------------------

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=escola,
        ativo=True,
    )

    # --------------------------------------------------------
    # 5. Buscar turma somente se informada
    # --------------------------------------------------------

    turma = None

    if turma_id:

        turma = get_object_or_404(
            Turma,
            id=turma_id,
            escola=escola,
            ano_letivo=ano_ativo,
        )

    # --------------------------------------------------------
    # 6. Verificar se já existe matrícula nesse ano
    # --------------------------------------------------------

    matricula_existente = (
        Matricula.objects.filter(
            aluno=aluno,
            ano_letivo=ano_ativo,
        )
        .select_related("turma")
        .first()
    )

    if matricula_existente:

        turma_existente = (
            matricula_existente.turma.nome
            if matricula_existente.turma
            else "não definida"
        )

        return JsonResponse(
            {
                "success": False,
                "mensagem": (
                    f"O aluno {aluno.nome} já possui uma matrícula "
                    f"para o ano letivo {ano_ativo.ano}, "
                    f"na turma {turma_existente}."
                ),
            },
            status=409,
        )

    # --------------------------------------------------------
    # 7. Criar matrícula
    # --------------------------------------------------------

    try:

        with transaction.atomic():

            aluno_ja_esta_na_turma = False

            if turma:

                aluno_ja_esta_na_turma = turma.alunos.filter(id=aluno.id).exists()

            matricula = Matricula.objects.create(
                aluno=aluno,
                ano_letivo=ano_ativo,
                turma=turma,
                data_matricula=timezone.now().date(),
                status="ATIVA",
            )

            if turma:

                aluno.turmas.add(turma)

    except IntegrityError:

        return JsonResponse(
            {
                "success": False,
                "mensagem": (
                    f"O aluno {aluno.nome} já possui uma matrícula "
                    f"para o ano letivo {ano_ativo.ano}."
                ),
            },
            status=409,
        )

    # --------------------------------------------------------
    # 8. Mensagem de sucesso
    # --------------------------------------------------------

    if not turma:

        mensagem = (
            f"Matrícula de {aluno.nome} realizada com sucesso "
            f"para o ano letivo {ano_ativo.ano}. "
            f"A turma ainda não foi definida."
        )

    elif aluno_ja_esta_na_turma:

        mensagem = (
            f"Matrícula de {aluno.nome} realizada com sucesso "
            f"para o ano letivo {ano_ativo.ano}. "
            f"O aluno já estava vinculado à turma "
            f"{turma.nome}."
        )

    else:

        mensagem = (
            f"Matrícula de {aluno.nome} realizada com sucesso "
            f"para o ano letivo {ano_ativo.ano}. "
            f"O aluno foi vinculado à turma {turma.nome}."
        )

    # --------------------------------------------------------
    # 9. Retorno de sucesso
    # --------------------------------------------------------

    return JsonResponse(
        {
            "success": True,
            "mensagem": mensagem,
            "matricula_id": matricula.id,
            "aluno_id": aluno.id,
            "turma_id": turma.id if turma else None,
            "ano_letivo": ano_ativo.ano,
            "aluno_ja_estava_na_turma": aluno_ja_esta_na_turma,
        },
        status=201,
    )


# ============================================================
# VISUALIZAR MATRÍCULA
# ============================================================


@login_required
@role_required(["diretor", "coordenador"])
def visualizar_matricula(request, matricula_id):

    escola = request.escola
    ano_ativo = get_ano_ativo()

    if not ano_ativo:

        return render(
            request,
            "pages/visualizar_matricula.html",
            {
                "ano_ativo": None,
                "matricula": None,
            },
        )

    matricula = get_object_or_404(
        Matricula.objects.select_related(
            "aluno",
            "turma",
            "ano_letivo",
        ),
        id=matricula_id,
        ano_letivo=ano_ativo,
        aluno__escola=escola,
    )

    return render(
        request,
        "pages/visualizar_matricula.html",
        {
            "ano_ativo": ano_ativo,
            "matricula": matricula,
        },
    )


# ============================================================
# EDITAR MATRÍCULA - TELA
# ============================================================


@login_required
@role_required(["diretor", "coordenador"])
def editar_matricula(request, matricula_id):

    escola = request.escola
    ano_ativo = get_ano_ativo()

    if not ano_ativo:

        return render(
            request,
            "pages/editar_matricula.html",
            {
                "ano_ativo": None,
                "matricula": None,
                "turmas": [],
            },
        )

    matricula = get_object_or_404(
        Matricula.objects.select_related(
            "aluno",
            "turma",
            "ano_letivo",
        ),
        id=matricula_id,
        ano_letivo=ano_ativo,
        aluno__escola=escola,
    )

    turmas = Turma.objects.filter(
        escola=escola,
        ano_letivo=ano_ativo,
    ).order_by("nome")

    return render(
        request,
        "pages/editar_matricula.html",
        {
            "ano_ativo": ano_ativo,
            "matricula": matricula,
            "turmas": turmas,
        },
    )


# ============================================================
# SALVAR EDIÇÃO DA MATRÍCULA
# ============================================================


@login_required
@role_required(["diretor", "coordenador"])
@require_POST
def salvar_edicao_matricula(request, matricula_id):

    escola = request.escola
    ano_ativo = get_ano_ativo()

    # --------------------------------------------------------
    # 1. Verificar ano letivo ativo
    # --------------------------------------------------------

    if not ano_ativo:

        return JsonResponse(
            {
                "success": False,
                "mensagem": (
                    "Não existe um ano letivo ativo " "para editar a matrícula."
                ),
            },
            status=400,
        )

    # --------------------------------------------------------
    # 2. Buscar matrícula
    # --------------------------------------------------------

    matricula = get_object_or_404(
        Matricula.objects.select_related(
            "aluno",
            "turma",
            "ano_letivo",
        ),
        id=matricula_id,
        ano_letivo=ano_ativo,
        aluno__escola=escola,
    )

    # --------------------------------------------------------
    # 3. Ler JSON
    # --------------------------------------------------------

    try:

        data = json.loads(request.body or "{}")

    except (json.JSONDecodeError, TypeError):

        return JsonResponse(
            {
                "success": False,
                "mensagem": "Dados da matrícula inválidos.",
            },
            status=400,
        )

    turma_id = data.get("turma_id")
    status_matricula = (data.get("status") or "").strip().upper()
    observacao = (data.get("observacao") or "").strip()

    # --------------------------------------------------------
    # 4. Validar status
    # --------------------------------------------------------

    status_validos = {
        "ATIVA",
        "CONCLUIDA",
        "TRANSFERIDA",
        "CANCELADA",
    }

    if status_matricula not in status_validos:

        return JsonResponse(
            {
                "success": False,
                "mensagem": "Status de matrícula inválido.",
            },
            status=400,
        )

    # --------------------------------------------------------
    # 5. Buscar nova turma, se informada
    # --------------------------------------------------------

    nova_turma = None

    if turma_id:

        nova_turma = get_object_or_404(
            Turma,
            id=turma_id,
            escola=escola,
            ano_letivo=ano_ativo,
        )

    turma_anterior = matricula.turma

    # --------------------------------------------------------
    # 6. Atualizar matrícula
    # --------------------------------------------------------

    try:

        with transaction.atomic():

            matricula.turma = nova_turma
            matricula.status = status_matricula
            matricula.observacao = observacao

            matricula.save(
                update_fields=[
                    "turma",
                    "status",
                    "observacao",
                    "atualizado_em",
                ]
            )

            # ------------------------------------------------
            # Remover vínculo operacional da turma anterior
            # ------------------------------------------------

            if turma_anterior and turma_anterior.id != (
                nova_turma.id if nova_turma else None
            ):

                matricula.aluno.turmas.remove(turma_anterior)

                if matricula.aluno.turma_principal_id == turma_anterior.id:

                    matricula.aluno.turma_principal = None

                    matricula.aluno.save(update_fields=["turma_principal"])

            # ------------------------------------------------
            # Adicionar vínculo operacional da nova turma
            # ------------------------------------------------

            if nova_turma:

                matricula.aluno.turmas.add(nova_turma)

                matricula.aluno.turma_principal = nova_turma

                matricula.aluno.save(update_fields=["turma_principal"])

    except IntegrityError:

        return JsonResponse(
            {
                "success": False,
                "mensagem": ("Não foi possível atualizar " "a matrícula."),
            },
            status=409,
        )

    # --------------------------------------------------------
    # 7. Retorno
    # --------------------------------------------------------

    return JsonResponse(
        {
            "success": True,
            "mensagem": (
                f"Matrícula de {matricula.aluno.nome} " f"atualizada com sucesso."
            ),
            "matricula_id": matricula.id,
            "turma_id": (nova_turma.id if nova_turma else None),
            "status": matricula.status,
        },
        status=200,
    )


@login_required
@role_required(["diretor", "coordenador"])
def declaracao_matrícula(request, matricula_id):

    escola = request.escola

    matricula = get_object_or_404(
        Matricula.objects.select_related(
            "aluno",
            "ano_letivo",
            "turma",
        ),
        id=matricula_id,
        aluno__escola=escola,
    )

    return render(
        request,
        "pages/declaracao_de_matrícula.html",
        {
            "matricula": matricula,
            "escola": escola,
        },
    )
