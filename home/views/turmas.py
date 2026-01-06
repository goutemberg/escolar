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

    turmas_qs = (
        Turma.objects
        .filter(escola=request.user.escola)
        .prefetch_related("alunos")
        .order_by("nome")
    )

    turmas = []

    for turma in turmas_qs:
        professores = (
            TurmaDisciplina.objects
            .filter(turma=turma)
            .select_related("professor")
            .values_list("professor__nome", flat=True)
            .distinct()
        )

        turmas.append({
            "obj": turma,
            "professores": list(professores),
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

