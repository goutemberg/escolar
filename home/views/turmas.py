from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from home.models import User
from home.utils import get_ano_ativo
import json
from home.models import (
    Turma,
    TurmaDisciplina,
    Disciplina,
    Aluno,
    NomeTurma,
    Chamada,
    TipoAvaliacao,
    ModeloAvaliacao,
    Avaliacao,
)

from home.decorators import role_required
from home.models import Matricula

# ======================================================
# LISTAGEM DE TURMAS
# ======================================================


@login_required
def listar_turmas(request):
    ano_ativo = get_ano_ativo()

    if ano_ativo:
        turmas_qs = (
            Turma.objects.filter(
                escola=request.escola,
                ano_letivo=ano_ativo,
            )
            .prefetch_related("alunos")
            .order_by("nome")
        )
    else:
        turmas_qs = Turma.objects.none()

    turmas = []
    turmas_json = []

    for turma in turmas_qs:
        professores = (
            TurmaDisciplina.objects.filter(turma=turma)
            .select_related("professor")
            .values_list("professor__nome", flat=True)
            .distinct()
        )

        turmas.append(
            {
                "obj": turma,
                "professores": list(professores),
            }
        )

        turmas_json.append(
            {
                "id": turma.id,
                "nome": turma.nome,
                "sala": turma.sala,
                "ano": turma.ano,
                "turno": turma.turno,
                "descricao": turma.descricao or "",
                "sistema_avaliacao": turma.sistema_avaliacao or "NUM",
            }
        )

    return render(
        request,
        "pages/turmas/listar_turmas.html",
        {
            "turmas": turmas,
            "turmas_json": json.dumps(
                turmas_json,
                ensure_ascii=False,
            ),
        },
    )


# ======================================================
# DETALHE DA TURMA
# ======================================================
@login_required
def detalhe_turma(request, turma_id):
    escola = request.escola

    turma = get_object_or_404(Turma, id=turma_id, escola=escola)

    # Alunos ativos
    alunos = turma.alunos.filter(ativo=True).order_by("nome")

    # Vínculos pedagógicos (professor + disciplina)
    disciplinas = (
        TurmaDisciplina.objects.filter(turma=turma)
        .select_related("disciplina", "professor")
        .order_by("disciplina__nome")
    )

    # Professores extraídos dos vínculos (sem duplicar)
    professores = {td.professor for td in disciplinas if td.professor}

    return render(
        request,
        "pages/turmas/detalhe_turma.html",
        {
            "turma": turma,
            "alunos": alunos,
            "disciplinas": disciplinas,
            "professores": professores,
        },
    )


# ======================================================
# PÁGINA DE CADASTRO DE NOME DE TURMA
# ======================================================
@login_required
def pagina_nome_turma(request):
    return render(request, "pages/nome_turma.html")


# ======================================================
# CADASTRAR NOME DE TURMA (AJAX)
# ======================================================
@login_required
def cadastrar_nome_turma(request):
    data = json.loads(request.body)
    nome = data.get("nome")

    if not nome:
        return JsonResponse({"success": False, "error": "Nome não informado."})

    if NomeTurma.objects.filter(nome=nome, escola=request.escola).exists():
        return JsonResponse({"success": False, "error": "Nome já cadastrado."})

    NomeTurma.objects.create(nome=nome, escola=request.escola)

    return JsonResponse({"success": True})


# ======================================================
# LISTAR NOMES DE TURMA (AJAX)
# ======================================================
@login_required
def listar_nomes_turma(request):
    nomes = (
        NomeTurma.objects.filter(escola=request.escola)
        .values("id", "nome")
        .order_by("nome")
    )

    return JsonResponse({"nomes": list(nomes)})


# ======================================================
# EDITAR NOME DE TURMA (AJAX)
# ======================================================
@login_required
def editar_nome_turma(request):
    data = json.loads(request.body)

    try:
        id = int(data.get("id"))
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "ID inválido."})

    nome = data.get("nome")

    if not nome:
        return JsonResponse({"success": False, "error": "Nome não informado."})

    obj = NomeTurma.objects.filter(id=id, escola=request.escola).first()

    if not obj:
        return JsonResponse({"success": False, "error": "Registro não encontrado."})

    obj.nome = nome
    obj.save()

    return JsonResponse({"success": True})


# ======================================================
# EXCLUIR NOME DE TURMA (AJAX)
# ======================================================
@login_required
def excluir_nome_turma(request):
    data = json.loads(request.body)
    id = data.get("id")

    if not id:
        return JsonResponse({"success": False, "error": "ID não informado."})

    NomeTurma.objects.filter(id=id, escola=request.escola).delete()

    return JsonResponse({"success": True})


@login_required
@role_required(["diretor", "coordenador"])
def cadastro_turma(request, turma_id=None):

    if request.method == "POST":
        return _salvar_turma(request)

    escola = request.escola

    disciplinas = Disciplina.objects.filter(escola=escola).order_by("nome")

    nomes_turma = NomeTurma.objects.filter(escola=escola).order_by("nome")

    coordenadores = (
        User.objects.filter(
            escola=escola,
            roles__nome="coordenador",
            is_active=True,
        )
        .distinct()
        .order_by("first_name", "last_name")
    )

    turma = None

    if turma_id:
        turma = Turma.objects.filter(id=turma_id, escola=escola).first()

    return render(
        request,
        "pages/registrar_turma.html",
        {
            "disciplinas": disciplinas,
            "nomes_turma": nomes_turma,
            "turma": turma,
            "coordenadores": coordenadores,
        },
    )


##########################################
# Com validacao de matricula ativa
##########################################

# def _salvar_turma(request):

#     escola = request.escola

#     try:
#         data = json.loads(request.body)

#         turma_id = data.get("turma_id")

#         nome = data.get("nome")
#         turno = data.get("turno")
#         sala = data.get("sala")
#         descricao = data.get("descricao", "")
#         alunos_ids = data.get("alunos_ids", [])
#         professores = data.get("professores", [])
#         coordenadores_ids = data.get("coordenadores_ids", [])

#         sistema_avaliacao = (data.get("sistema_avaliacao") or "NUM").strip().upper()

#         tipo_turma = (data.get("tipo_turma") or "FUN").strip().upper()

#         if tipo_turma not in ("INF", "FUN", "MED"):
#             tipo_turma = "FUN"

#         polivalente = data.get("polivalente", False)

#         if isinstance(polivalente, str):
#             polivalente = polivalente.lower() in (
#                 "true",
#                 "1",
#                 "sim",
#                 "on",
#             )
#         else:
#             polivalente = bool(polivalente)

#         if sistema_avaliacao not in ("NUM", "CON"):
#             sistema_avaliacao = "NUM"

#         # =========================================================
#         # 🔹 VALIDAÇÃO DO ANO
#         # =========================================================

#         try:
#             ano = int(data.get("ano"))
#         except (TypeError, ValueError):

#             return JsonResponse(
#                 {
#                     "success": False,
#                     "mensagem": "Ano inválido.",
#                 },
#                 status=400,
#             )

#         if not all([nome, turno, ano, sala]):

#             return JsonResponse(
#                 {
#                     "success": False,
#                     "mensagem": "Preencha os dados básicos da turma.",
#                 },
#                 status=400,
#             )

#         # =========================================================
#         # 🔹 ANO LETIVO ATIVO
#         # =========================================================

#         ano_letivo = get_ano_ativo()

#         if not ano_letivo:

#             return JsonResponse(
#                 {
#                     "success": False,
#                     "mensagem": (
#                         "Não existe um ano letivo ativo " "para cadastrar a turma."
#                     ),
#                 },
#                 status=400,
#             )

#         # =========================================================
#         # 🔹 NORMALIZAÇÃO DOS ALUNOS
#         # =========================================================

#         alunos_ids_normalizados = set()

#         if alunos_ids:

#             try:
#                 alunos_ids_normalizados = {int(aluno_id) for aluno_id in alunos_ids}

#             except (TypeError, ValueError):

#                 return JsonResponse(
#                     {
#                         "success": False,
#                         "mensagem": "Lista de alunos inválida.",
#                     },
#                     status=400,
#                 )

#         with transaction.atomic():

#             # =========================================================
#             # 🔹 CRIAR / ATUALIZAR TURMA
#             # =========================================================

#             if not turma_id:

#                 turma = Turma.objects.create(
#                     nome=nome,
#                     turno=turno,
#                     ano=ano,
#                     ano_letivo=ano_letivo,
#                     sala=sala,
#                     descricao=descricao,
#                     escola=escola,
#                     sistema_avaliacao=sistema_avaliacao,
#                     tipo_turma=tipo_turma,
#                     polivalente=polivalente,
#                 )

#             else:

#                 turma = get_object_or_404(
#                     Turma,
#                     id=turma_id,
#                     escola=escola,
#                 )

#                 turma.nome = nome
#                 turma.turno = turno
#                 turma.ano = ano
#                 turma.sala = sala
#                 turma.descricao = descricao
#                 turma.sistema_avaliacao = sistema_avaliacao
#                 turma.tipo_turma = tipo_turma
#                 turma.polivalente = polivalente

#                 turma.save()

#                 # =====================================================
#                 # 🔹 ALUNOS ATUAIS DA TURMA
#                 # =====================================================

#                 alunos_atuais_ids = set(
#                     turma.alunos.values_list(
#                         "id",
#                         flat=True,
#                     )
#                 )

#                 # =====================================================
#                 # 🔹 REMOVER SOMENTE OS ALUNOS DESTA TURMA
#                 # =====================================================

#                 alunos_remover_ids = alunos_atuais_ids - alunos_ids_normalizados

#                 if alunos_remover_ids:

#                     alunos_remover = Aluno.objects.filter(
#                         id__in=alunos_remover_ids,
#                         escola=escola,
#                     )

#                     for aluno in alunos_remover:

#                         # -------------------------------------------------
#                         # Remove somente esta turma.
#                         # -------------------------------------------------

#                         aluno.turmas.remove(turma)

#                         # -------------------------------------------------
#                         # Mantém a regra existente do turma_principal:
#                         # só limpa se esta era realmente a turma principal.
#                         # -------------------------------------------------

#                         if aluno.turma_principal_id == turma.id:

#                             aluno.turma_principal = None

#                             aluno.save(update_fields=["turma_principal"])

#                         # -------------------------------------------------
#                         # Matrícula anual:
#                         # mantém a matrícula ATIVA, mas remove a turma.
#                         #
#                         # O aluno continua matriculado no ano e poderá
#                         # posteriormente ser colocado em outra turma.
#                         # -------------------------------------------------

#                         Matricula.objects.filter(
#                             aluno=aluno,
#                             ano_letivo=ano_letivo,
#                             status="ATIVA",
#                             turma=turma,
#                         ).update(
#                             turma=None,
#                             atualizado_em=timezone.now(),
#                         )

#                 # =====================================================
#                 # 🔹 DISCIPLINAS DA TURMA
#                 # =====================================================

#                 TurmaDisciplina.objects.filter(
#                     turma=turma,
#                     escola=escola,
#                 ).delete()

#             # =========================================================
#             # 🔹 COORDENADORES
#             # =========================================================

#             turma.coordenadores.set(coordenadores_ids)

#             # =========================================================
#             # 🔹 ALUNOS
#             # =========================================================

#             # ---------------------------------------------------------
#             # Somente alunos com matrícula ATIVA no ano letivo da turma
#             # ---------------------------------------------------------

#             matriculas_ativas = Matricula.objects.filter(
#                 aluno__id__in=alunos_ids_normalizados,
#                 aluno__escola=escola,
#                 aluno__ativo=True,
#                 ano_letivo=ano_letivo,
#                 status="ATIVA",
#             ).select_related("aluno")

#             matriculas_por_aluno = {
#                 matricula.aluno_id: matricula for matricula in matriculas_ativas
#             }

#             # =========================================================
#             # 🔹 BLOQUEIA ALUNO SEM MATRÍCULA ATIVA
#             # =========================================================

#             alunos_sem_matricula = alunos_ids_normalizados - set(
#                 matriculas_por_aluno.keys()
#             )

#             if alunos_sem_matricula:

#                 return JsonResponse(
#                     {
#                         "success": False,
#                         "mensagem": (
#                             "Um ou mais alunos selecionados "
#                             "não possuem matrícula ativa "
#                             "neste ano letivo."
#                         ),
#                     },
#                     status=400,
#                 )

#             # =========================================================
#             # 🔹 BUSCA ALUNOS VÁLIDOS
#             # =========================================================

#             alunos = Aluno.objects.filter(
#                 id__in=alunos_ids_normalizados,
#                 escola=escola,
#                 ativo=True,
#             )

#             for aluno in alunos:

#                 matricula = matriculas_por_aluno.get(aluno.id)

#                 if not matricula:
#                     continue

#                 # =====================================================
#                 # Atualiza a matrícula anual
#                 #
#                 # Se estava sem turma, passa a apontar para esta turma.
#                 # =====================================================

#                 matricula.turma = turma

#                 matricula.save(
#                     update_fields=[
#                         "turma",
#                         "atualizado_em",
#                     ]
#                 )

#                 # =====================================================
#                 # Mantém compatibilidade com a estrutura atual
#                 # =====================================================

#                 aluno.turmas.add(turma)

#                 # -----------------------------------------------------
#                 # O aluno selecionado passa a ter esta turma como
#                 # turma principal.
#                 # -----------------------------------------------------

#                 aluno.turma_principal = turma

#                 aluno.save(update_fields=["turma_principal"])

#             # =========================================================
#             # 🔹 PROFESSORES + DISCIPLINAS
#             # =========================================================

#             for item in professores:

#                 TurmaDisciplina.objects.create(
#                     turma=turma,
#                     professor_id=item.get("professor_id"),
#                     disciplina_id=(
#                         item.get("disciplinas_id") or item.get("disciplina_id")
#                     ),
#                     escola=escola,
#                 )

#             # =========================================================
#             # 🔹 DISCIPLINAS
#             # =========================================================

#             disciplinas_turma = Disciplina.objects.filter(
#                 turmadisciplina__turma=turma
#             ).distinct()

#             tipo_prova, _ = TipoAvaliacao.objects.get_or_create(
#                 escola=escola,
#                 nome="Prova",
#             )

#             tipo_trabalho, _ = TipoAvaliacao.objects.get_or_create(
#                 escola=escola,
#                 nome="Trabalho",
#             )

#             # =========================================================
#             # 🔹 MODELOS DE AVALIAÇÃO
#             # =========================================================

#             for disciplina in disciplinas_turma:

#                 if not ModeloAvaliacao.objects.filter(
#                     escola=escola,
#                     disciplina=disciplina,
#                 ).exists():

#                     ModeloAvaliacao.objects.create(
#                         nome="Prova",
#                         tipo=tipo_prova,
#                         peso=7,
#                         quantidade=3,
#                         escola=escola,
#                         disciplina=disciplina,
#                         ativo=True,
#                     )

#                     ModeloAvaliacao.objects.create(
#                         nome="Trabalho",
#                         tipo=tipo_trabalho,
#                         peso=3,
#                         quantidade=1,
#                         escola=escola,
#                         disciplina=disciplina,
#                         ativo=True,
#                     )

#             # =========================================================
#             # 🔹 BIMESTRES / AVALIAÇÕES
#             # =========================================================

#             bimestres = [1, 2, 3, 4]

#             for disciplina in disciplinas_turma:

#                 modelos = ModeloAvaliacao.objects.filter(
#                     escola=escola,
#                     disciplina=disciplina,
#                     ativo=True,
#                 )

#                 for bimestre in bimestres:

#                     for modelo in modelos:

#                         for i in range(
#                             1,
#                             modelo.quantidade + 1,
#                         ):

#                             nome_avaliacao = (
#                                 f"{modelo.nome} {i}"
#                                 if modelo.quantidade > 1
#                                 else modelo.nome
#                             )

#                             Avaliacao.objects.get_or_create(
#                                 turma=turma,
#                                 disciplina=disciplina,
#                                 bimestre=bimestre,
#                                 descricao=nome_avaliacao,
#                                 escola=escola,
#                                 defaults={
#                                     "tipo": modelo.tipo,
#                                     "data": timezone.now().date(),
#                                 },
#                             )

#         # =========================================================
#         # 🔹 ATUALIZA TURMA
#         # =========================================================

#         turma.refresh_from_db()

#         return JsonResponse(
#             {
#                 "success": True,
#                 "mensagem": "Turma salva com sucesso.",
#                 "turma_id": turma.id,
#             }
#         )

#     except Exception as e:

#         import traceback

#         traceback.print_exc()

#         return JsonResponse(
#             {
#                 "success": False,
#                 "mensagem": (f"Erro ao salvar turma: {str(e)}"),
#             },
#             status=500,
#         )


##########################################
# Sem validacao de matricula ativa
##########################################


def _salvar_turma(request):

    escola = request.escola

    try:
        data = json.loads(request.body)

        turma_id = data.get("turma_id")

        nome = data.get("nome")
        turno = data.get("turno")
        sala = data.get("sala")
        descricao = data.get("descricao", "")
        alunos_ids = data.get("alunos_ids", [])
        professores = data.get("professores", [])
        coordenadores_ids = data.get("coordenadores_ids", [])

        sistema_avaliacao = (data.get("sistema_avaliacao") or "NUM").strip().upper()

        tipo_turma = (data.get("tipo_turma") or "FUN").strip().upper()

        if tipo_turma not in ("INF", "FUN", "MED"):
            tipo_turma = "FUN"

        polivalente = data.get("polivalente", False)

        if isinstance(polivalente, str):
            polivalente = polivalente.lower() in (
                "true",
                "1",
                "sim",
                "on",
            )
        else:
            polivalente = bool(polivalente)

        if sistema_avaliacao not in ("NUM", "CON"):
            sistema_avaliacao = "NUM"

        # =========================================================
        # 🔹 VALIDAÇÃO DO ANO
        # =========================================================

        try:
            ano = int(data.get("ano"))
        except (TypeError, ValueError):

            return JsonResponse(
                {
                    "success": False,
                    "mensagem": "Ano inválido.",
                },
                status=400,
            )

        if not all([nome, turno, ano, sala]):

            return JsonResponse(
                {
                    "success": False,
                    "mensagem": "Preencha os dados básicos da turma.",
                },
                status=400,
            )

        # =========================================================
        # 🔹 ANO LETIVO ATIVO
        # =========================================================

        ano_letivo = get_ano_ativo()

        if not ano_letivo:

            return JsonResponse(
                {
                    "success": False,
                    "mensagem": (
                        "Não existe um ano letivo ativo " "para cadastrar a turma."
                    ),
                },
                status=400,
            )

        # =========================================================
        # 🔹 NORMALIZAÇÃO DOS ALUNOS
        # =========================================================

        alunos_ids_normalizados = set()

        if alunos_ids:

            try:
                alunos_ids_normalizados = {int(aluno_id) for aluno_id in alunos_ids}

            except (TypeError, ValueError):

                return JsonResponse(
                    {
                        "success": False,
                        "mensagem": "Lista de alunos inválida.",
                    },
                    status=400,
                )

        with transaction.atomic():

            # =========================================================
            # 🔹 CRIAR / ATUALIZAR TURMA
            # =========================================================

            if not turma_id:

                turma = Turma.objects.create(
                    nome=nome,
                    turno=turno,
                    ano=ano,
                    ano_letivo=ano_letivo,
                    sala=sala,
                    descricao=descricao,
                    escola=escola,
                    sistema_avaliacao=sistema_avaliacao,
                    tipo_turma=tipo_turma,
                    polivalente=polivalente,
                )

            else:

                turma = get_object_or_404(
                    Turma,
                    id=turma_id,
                    escola=escola,
                )

                turma.nome = nome
                turma.turno = turno
                turma.ano = ano
                turma.sala = sala
                turma.descricao = descricao
                turma.sistema_avaliacao = sistema_avaliacao
                turma.tipo_turma = tipo_turma
                turma.polivalente = polivalente

                turma.save()

                # =====================================================
                # 🔹 ALUNOS ATUAIS DA TURMA
                # =====================================================

                alunos_atuais_ids = set(
                    turma.alunos.values_list(
                        "id",
                        flat=True,
                    )
                )

                # =====================================================
                # 🔹 REMOVER SOMENTE OS ALUNOS DESTA TURMA
                # =====================================================

                alunos_remover_ids = alunos_atuais_ids - alunos_ids_normalizados

                if alunos_remover_ids:

                    alunos_remover = Aluno.objects.filter(
                        id__in=alunos_remover_ids,
                        escola=escola,
                    )

                    for aluno in alunos_remover:

                        # -------------------------------------------------
                        # Remove somente esta turma.
                        # -------------------------------------------------

                        aluno.turmas.remove(turma)

                        # -------------------------------------------------
                        # Mantém a regra existente do turma_principal:
                        # só limpa se esta era realmente a turma principal.
                        # -------------------------------------------------

                        if aluno.turma_principal_id == turma.id:

                            aluno.turma_principal = None

                            aluno.save(update_fields=["turma_principal"])

                        # -------------------------------------------------
                        # Matrícula anual:
                        # mantém a matrícula ATIVA, mas remove a turma.
                        #
                        # O aluno continua matriculado no ano e poderá
                        # posteriormente ser colocado em outra turma.
                        # -------------------------------------------------

                        Matricula.objects.filter(
                            aluno=aluno,
                            ano_letivo=ano_letivo,
                            status="ATIVA",
                            turma=turma,
                        ).update(
                            turma=None,
                            atualizado_em=timezone.now(),
                        )

                # =====================================================
                # 🔹 DISCIPLINAS DA TURMA
                # =====================================================

                TurmaDisciplina.objects.filter(
                    turma=turma,
                    escola=escola,
                ).delete()

            # =========================================================
            # 🔹 COORDENADORES
            # =========================================================

            turma.coordenadores.set(coordenadores_ids)

            # =========================================================
            # 🔹 ALUNOS
            # =========================================================
            #
            # A matrícula NÃO é obrigatória durante o ano letivo.
            #
            # A validação oficial da situação dos alunos será realizada
            # no fechamento do ano letivo.
            #
            # Caso exista uma matrícula ATIVA, ela continua sendo
            # atualizada para apontar para a turma.
            # =========================================================

            matriculas_ativas = Matricula.objects.filter(
                aluno__id__in=alunos_ids_normalizados,
                aluno__escola=escola,
                aluno__ativo=True,
                ano_letivo=ano_letivo,
                status="ATIVA",
            ).select_related("aluno")

            matriculas_por_aluno = {
                matricula.aluno_id: matricula for matricula in matriculas_ativas
            }

            # =========================================================
            # 🔹 BUSCA ALUNOS VÁLIDOS
            # =========================================================

            alunos = Aluno.objects.filter(
                id__in=alunos_ids_normalizados,
                escola=escola,
                ativo=True,
            )

            for aluno in alunos:

                # =====================================================
                # Matrícula é opcional durante o ano letivo.
                #
                # Se existir matrícula ativa, atualiza a turma.
                # Se não existir, o aluno continua podendo pertencer
                # à turma normalmente.
                # =====================================================

                matricula = matriculas_por_aluno.get(aluno.id)

                if matricula:

                    matricula.turma = turma

                    matricula.save(
                        update_fields=[
                            "turma",
                            "atualizado_em",
                        ]
                    )

                # =====================================================
                # Mantém compatibilidade com a estrutura atual
                # =====================================================

                aluno.turmas.add(turma)

                # -----------------------------------------------------
                # O aluno selecionado passa a ter esta turma como
                # turma principal.
                # -----------------------------------------------------

                aluno.turma_principal = turma

                aluno.save(update_fields=["turma_principal"])

            # =========================================================
            # 🔹 PROFESSORES + DISCIPLINAS
            # =========================================================

            for item in professores:

                TurmaDisciplina.objects.create(
                    turma=turma,
                    professor_id=item.get("professor_id"),
                    disciplina_id=(
                        item.get("disciplinas_id") or item.get("disciplina_id")
                    ),
                    escola=escola,
                )

            # =========================================================
            # 🔹 DISCIPLINAS
            # =========================================================

            disciplinas_turma = Disciplina.objects.filter(
                turmadisciplina__turma=turma
            ).distinct()

            tipo_prova, _ = TipoAvaliacao.objects.get_or_create(
                escola=escola,
                nome="Prova",
            )

            tipo_trabalho, _ = TipoAvaliacao.objects.get_or_create(
                escola=escola,
                nome="Trabalho",
            )

            # =========================================================
            # 🔹 MODELOS DE AVALIAÇÃO
            # =========================================================

            for disciplina in disciplinas_turma:

                if not ModeloAvaliacao.objects.filter(
                    escola=escola,
                    disciplina=disciplina,
                ).exists():

                    ModeloAvaliacao.objects.create(
                        nome="Prova",
                        tipo=tipo_prova,
                        peso=7,
                        quantidade=3,
                        escola=escola,
                        disciplina=disciplina,
                        ativo=True,
                    )

                    ModeloAvaliacao.objects.create(
                        nome="Trabalho",
                        tipo=tipo_trabalho,
                        peso=3,
                        quantidade=1,
                        escola=escola,
                        disciplina=disciplina,
                        ativo=True,
                    )

            # =========================================================
            # 🔹 BIMESTRES / AVALIAÇÕES
            # =========================================================

            bimestres = [1, 2, 3, 4]

            for disciplina in disciplinas_turma:

                modelos = ModeloAvaliacao.objects.filter(
                    escola=escola,
                    disciplina=disciplina,
                    ativo=True,
                )

                for bimestre in bimestres:

                    for modelo in modelos:

                        for i in range(
                            1,
                            modelo.quantidade + 1,
                        ):

                            nome_avaliacao = (
                                f"{modelo.nome} {i}"
                                if modelo.quantidade > 1
                                else modelo.nome
                            )

                            Avaliacao.objects.get_or_create(
                                turma=turma,
                                disciplina=disciplina,
                                bimestre=bimestre,
                                descricao=nome_avaliacao,
                                escola=escola,
                                defaults={
                                    "tipo": modelo.tipo,
                                    "data": timezone.now().date(),
                                },
                            )

        # =========================================================
        # 🔹 ATUALIZA TURMA
        # =========================================================

        turma.refresh_from_db()

        return JsonResponse(
            {
                "success": True,
                "mensagem": "Turma salva com sucesso.",
                "turma_id": turma.id,
            }
        )

    except Exception as e:

        import traceback

        traceback.print_exc()

        return JsonResponse(
            {
                "success": False,
                "mensagem": (f"Erro ao salvar turma: {str(e)}"),
            },
            status=500,
        )


@login_required
@role_required(["diretor", "coordenador"])
@transaction.atomic
def remover_aluno_turma(request, turma_id):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "mensagem": "Método inválido."}, status=405
        )

    escola = request.escola

    try:
        data = json.loads(request.body)
        aluno_id = data.get("aluno_id")

        if not aluno_id:
            return JsonResponse(
                {"success": False, "mensagem": "Aluno não informado."}, status=400
            )

        turma = get_object_or_404(Turma, id=turma_id, escola=escola)

        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)

        # remove vínculo
        turma.alunos.remove(aluno)

        if aluno.turma_principal_id == turma.id:
            aluno.turma_principal = None
            aluno.save(update_fields=["turma_principal"])

        return JsonResponse({"success": True})

    except Exception as e:
        transaction.set_rollback(True)
        return JsonResponse({"success": False, "mensagem": str(e)}, status=500)


# ======================================================
# Remover Professor da turma
# ======================================================


@login_required
@role_required(["diretor", "coordenador"])
@transaction.atomic
def remover_professor_turma(request, turma_id):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "mensagem": "Método inválido."}, status=405
        )

    escola = request.escola

    try:
        data = json.loads(request.body)
        professor_id = data.get("professor_id")

        if not professor_id:
            return JsonResponse(
                {"success": False, "mensagem": "Professor não informado."}, status=400
            )

        turma = get_object_or_404(Turma, id=turma_id, escola=escola)

        # remove TODOS os vínculos do professor com a turma
        TurmaDisciplina.objects.filter(
            turma=turma, professor_id=professor_id, escola=escola
        ).delete()

        return JsonResponse({"success": True})

    except Exception as e:
        transaction.set_rollback(True)
        return JsonResponse({"success": False, "mensagem": str(e)}, status=500)


@login_required
def api_detalhe_turma(request, turma_id):
    escola = request.escola

    turma = get_object_or_404(Turma, id=turma_id, escola=escola)

    alunos = list(turma.alunos.filter(ativo=True).values("id", "nome"))

    professores = list(
        TurmaDisciplina.objects.filter(turma=turma, escola=escola)
        .select_related("professor", "disciplina")
        .values("professor_id", "professor__nome", "disciplina_id", "disciplina__nome")
    )

    coordenadores = list(
        turma.coordenadores.values(
            "id",
            "first_name",
            "last_name",
            "username",
        )
    )

    return JsonResponse(
        {
            "id": turma.id,
            "nome": turma.nome,
            "turno": turma.turno,
            "ano": turma.ano,
            "sala": turma.sala,
            "descricao": turma.descricao,
            "sistema_avaliacao": turma.sistema_avaliacao,
            "alunos": alunos,
            "professores": [
                {
                    "professor_id": p["professor_id"],
                    "nome": p["professor__nome"],
                    "disciplina_id": p["disciplina_id"],
                    "disciplina_nome": p["disciplina__nome"],
                }
                for p in professores
            ],
            "coordenadores": [
                {
                    "id": c["id"],
                    "nome": (
                        f'{c["first_name"]} {c["last_name"]}'.strip() or c["username"]
                    ),
                }
                for c in coordenadores
            ],
        }
    )


@login_required
def inativar_turma(request, turma_id):

    turma = get_object_or_404(Turma, id=turma_id, escola=request.escola)

    if turma.status == "INATIVA":
        turma.status = "ATIVA"
    else:
        turma.status = "INATIVA"

    turma.save()

    return JsonResponse({"success": True})


@login_required
def excluir_turma(request, turma_id):

    turma = get_object_or_404(Turma, id=turma_id, escola=request.escola)

    if Chamada.objects.filter(
        turma=turma,
        escola=request.escola,
    ).exists():
        return JsonResponse(
            {"success": False, "error": "Turma possui registros acadêmicos."}
        )

    turma.delete()

    return JsonResponse({"success": True})


@login_required
def duplicar_turma(request, turma_id):

    turma = get_object_or_404(Turma, id=turma_id, escola=request.escola)

    nova_turma = Turma.objects.create(
        nome=turma.nome,
        turno=turma.turno,
        ano=turma.ano + 1,
        sala=turma.sala,
        descricao=turma.descricao,
        sistema_avaliacao=turma.sistema_avaliacao,
        escola=turma.escola,
    )

    return JsonResponse({"success": True, "nova_turma_id": nova_turma.id})
