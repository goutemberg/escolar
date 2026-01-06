from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
import json

from home.models import (
    Turma,
    TurmaDisciplina,
    Disciplina,
    Aluno,
    NomeTurma
)

from home.decorators import role_required


# ======================================================
# LISTAGEM DE TURMAS
# ======================================================
@login_required
def listar_turmas(request):
    escola = request.user.escola

    turmas_qs = (
        Turma.objects
        .filter(escola=escola)
        .prefetch_related("alunos")
        .order_by("nome")
    )

    # pré-carrega todos os vínculos de uma vez
    vinculos = (
        TurmaDisciplina.objects
        .filter(turma__in=turmas_qs)
        .select_related("professor", "turma")
    )

    mapa_professores = {}
    for v in vinculos:
        mapa_professores.setdefault(v.turma_id, set()).add(v.professor.nome)

    turmas = []
    for turma in turmas_qs:
        turmas.append({
            "turma": turma,
            "professores": sorted(mapa_professores.get(turma.id, []))
        })

    return render(request, "pages/turmas/listar_turmas.html", {
        "turmas": turmas
    })



# ======================================================
# DETALHE DA TURMA
# ======================================================
@login_required
def detalhe_turma(request, turma_id):
    escola = request.user.escola

    turma = get_object_or_404(
        Turma,
        id=turma_id,
        escola=escola
    )

    # Alunos ativos
    alunos = turma.alunos.filter(ativo=True).order_by("nome")

    # Vínculos pedagógicos (professor + disciplina)
    disciplinas = (
        TurmaDisciplina.objects
        .filter(turma=turma)
        .select_related("disciplina", "professor")
        .order_by("disciplina__nome")
    )

    # Professores extraídos dos vínculos (sem duplicar)
    professores = {
        td.professor for td in disciplinas if td.professor
    }

    return render(request, "pages/turmas/detalhe_turma.html", {
         "turma": turma,
         "alunos": alunos,
         "disciplinas": disciplinas,
         "professores": professores
    })


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

    if NomeTurma.objects.filter(nome=nome, escola=request.user.escola).exists():
        return JsonResponse({"success": False, "error": "Nome já cadastrado."})

    NomeTurma.objects.create(
        nome=nome,
        escola=request.user.escola
    )

    return JsonResponse({"success": True})


# ======================================================
# LISTAR NOMES DE TURMA (AJAX)
# ======================================================
@login_required
def listar_nomes_turma(request):
    nomes = (
        NomeTurma.objects
        .filter(escola=request.user.escola)
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

    obj = NomeTurma.objects.filter(
        id=id,
        escola=request.user.escola
    ).first()

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

    NomeTurma.objects.filter(
        id=id,
        escola=request.user.escola
    ).delete()

    return JsonResponse({"success": True})


@login_required
@role_required(['diretor', 'coordenador'])
def cadastro_turma(request):
    escola = request.user.escola

    # ======================================================
    # POST → SALVAR TURMA (API JSON)
    # ======================================================
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            nome = data.get('nome')
            turno = data.get('turno')
            sala = data.get('sala')
            descricao = data.get('descricao', '')
            alunos_ids = data.get('alunos_ids', [])
            professores = data.get('professores', [])

            # ano precisa ser inteiro
            try:
                ano = int(data.get('ano'))
            except (TypeError, ValueError):
                return JsonResponse({
                    'success': False,
                    'mensagem': 'Ano inválido.'
                }, status=400)

            # ✅ validação mínima (turma independe de professor)
            if not all([nome, turno, ano, sala]):
                return JsonResponse({
                    'success': False,
                    'mensagem': 'Preencha os dados básicos da turma.'
                }, status=400)

            with transaction.atomic():

                # 1️⃣ Criar Turma
                turma = Turma.objects.create(
                    nome=nome,
                    turno=turno,
                    ano=ano,
                    sala=sala,
                    descricao=descricao,
                    escola=escola
                )

                # 2️⃣ Associar Alunos (opcional)
                if alunos_ids:
                    alunos = Aluno.objects.filter(
                        id__in=alunos_ids,
                        escola=escola,
                        ativo=True
                    )
                    turma.alunos.add(*alunos)

                # 3️⃣ Associar Professores + Disciplinas (opcional, múltiplos)
                for item in professores:
                    TurmaDisciplina.objects.create(
                        turma=turma,
                        professor_id=item.get('professor_id'),
                        disciplina_id=item.get('disciplina_id'),
                        escola=escola
                    )

            return JsonResponse({
                'success': True,
                'mensagem': 'Turma criada com sucesso.',
                'turma_id': turma.id
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'mensagem': f'Erro ao salvar turma: {str(e)}'
            }, status=500)

    # ======================================================
    # GET → RENDERIZAR PÁGINA
    # ======================================================
    disciplinas = Disciplina.objects.filter(escola=escola).order_by('nome')
    nomes_turma = NomeTurma.objects.filter(escola=escola).order_by('nome')

    context = {
        'disciplinas': disciplinas,
        'nomes_turma': nomes_turma
    }

    return render(request, 'pages/registrar_turma.html', context)


# ======================================================
    # Remover aluno da turma
# ======================================================


@login_required
@role_required(['diretor', 'coordenador'])
@transaction.atomic
def remover_aluno_turma(request, turma_id):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "mensagem": "Método inválido."},
            status=405
        )

    escola = request.user.escola

    try:
        data = json.loads(request.body)
        aluno_id = data.get("aluno_id")

        if not aluno_id:
            return JsonResponse(
                {"success": False, "mensagem": "Aluno não informado."},
                status=400
            )

        turma = get_object_or_404(
            Turma,
            id=turma_id,
            escola=escola
        )

        aluno = get_object_or_404(
            Aluno,
            id=aluno_id,
            escola=escola
        )

        # remove vínculo
        turma.alunos.remove(aluno)

        return JsonResponse({"success": True})

    except Exception as e:
        transaction.set_rollback(True)
        return JsonResponse(
            {"success": False, "mensagem": str(e)},
            status=500
        )

# ======================================================
    # Remover Professor da turma
# ======================================================

@login_required
@role_required(['diretor', 'coordenador'])
@transaction.atomic
def remover_professor_turma(request, turma_id):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "mensagem": "Método inválido."},
            status=405
        )

    escola = request.user.escola

    try:
        data = json.loads(request.body)
        professor_id = data.get("professor_id")

        if not professor_id:
            return JsonResponse(
                {"success": False, "mensagem": "Professor não informado."},
                status=400
            )

        turma = get_object_or_404(
            Turma,
            id=turma_id,
            escola=escola
        )

        # remove TODOS os vínculos do professor com a turma
        TurmaDisciplina.objects.filter(
            turma=turma,
            professor_id=professor_id,
            escola=escola
        ).delete()

        return JsonResponse({"success": True})

    except Exception as e:
        transaction.set_rollback(True)
        return JsonResponse(
            {"success": False, "mensagem": str(e)},
            status=500
        )


# ======================================================
    # Remover Professor da turma
# ======================================================
@login_required
@role_required(['diretor', 'coordenador'])
@transaction.atomic
def atualizar_turma(request, turma_id):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "mensagem": "Método inválido."},
            status=405
        )

    escola = request.user.escola

    try:
        data = json.loads(request.body)

        nome = data.get("nome")
        turno = data.get("turno")
        sala = data.get("sala")
        descricao = data.get("descricao", "")
        alunos_ids = data.get("alunos_ids", [])
        professores = data.get("professores", [])

        # ano precisa ser inteiro
        try:
            ano = int(data.get("ano"))
        except (TypeError, ValueError):
            return JsonResponse(
                {"success": False, "mensagem": "Ano inválido."},
                status=400
            )

        if not all([nome, turno, ano, sala]):
            return JsonResponse(
                {"success": False, "mensagem": "Dados básicos da turma ausentes."},
                status=400
            )

        turma = get_object_or_404(
            Turma,
            id=turma_id,
            escola=escola
        )

        # 1️⃣ Atualiza dados básicos
        turma.nome = nome
        turma.turno = turno
        turma.ano = ano
        turma.sala = sala
        turma.descricao = descricao
        turma.save()

        # 2️⃣ Sincroniza alunos (estado final)
        alunos = Aluno.objects.filter(
            id__in=alunos_ids,
            escola=escola,
            ativo=True
        )
        turma.alunos.set(alunos)

        # 3️⃣ Sincroniza professores + disciplinas (estado final)
        TurmaDisciplina.objects.filter(
            turma=turma,
            escola=escola
        ).delete()

        for item in professores:
            TurmaDisciplina.objects.create(
                turma=turma,
                professor_id=item.get("professor_id"),
                disciplina_id=item.get("disciplina_id"),
                escola=escola
            )

        return JsonResponse({
            "success": True,
            "mensagem": "Turma atualizada com sucesso."
        })

    except Exception as e:
        transaction.set_rollback(True)
        return JsonResponse(
            {"success": False, "mensagem": str(e)},
            status=500
        )
