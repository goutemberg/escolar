from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import json

from home.models import Turma, TurmaDisciplina, Disciplina, Aluno

from django.http import JsonResponse
from home.models import NomeTurma
from home.decorators import role_required
from django.db import transaction


# ======================================================
# LISTAGEM DE TURMAS
# ======================================================
@login_required
def listar_turmas(request):

    turmas = (
        Turma.objects.filter(escola=request.user.escola)
        .prefetch_related("professores", "alunos")
        .order_by("nome")
    )

    return render(request, "pages/turmas/listar_turmas.html", {
        "turmas": turmas
    })


# ======================================================
# DETALHE DA TURMA
# ======================================================
@login_required
def detalhe_turma(request, turma_id):

    turma = get_object_or_404(
        Turma,
        id=turma_id,
        escola=request.user.escola
    )

    alunos = turma.alunos.filter(ativo=True).order_by("nome")
    professores = turma.professores.order_by("nome")
    disciplinas = (
        TurmaDisciplina.objects.filter(turma=turma)
        .select_related("disciplina", "professor")
        .order_by("disciplina__nome")
    )

    return render(request, "pages/turmas/detalhe_turma.html", {
        "turma": turma,
        "alunos": alunos,
        "professores": professores,
        "disciplinas": disciplinas
    })

def pagina_nome_turma(request):
    return render(request, "pages/nome_turma.html")

def cadastrar_nome_turma(request):
    data = json.loads(request.body)
    nome = data.get("nome")

    if NomeTurma.objects.filter(nome=nome, escola=request.user.escola).exists():
        return JsonResponse({"success": False, "error": "Nome já cadastrado."})

    NomeTurma.objects.create(nome=nome, escola=request.user.escola)
    return JsonResponse({"success": True})

def listar_nomes_turma(request):
    nomes = NomeTurma.objects.filter(escola=request.user.escola).values("id", "nome")
    return JsonResponse({"nomes": list(nomes)})

def editar_nome_turma(request):
    data = json.loads(request.body)

    try:
        id = int(data.get("id"))
    except:
        return JsonResponse({"success": False, "error": "ID inválido."})

    nome = data.get("nome")

    obj = NomeTurma.objects.filter(
        id=id,
        escola=request.user.escola
    ).first()

    if not obj:
        return JsonResponse({"success": False, "error": "Registro não encontrado."})

    obj.nome = nome
    obj.save()

    return JsonResponse({"success": True})


def excluir_nome_turma(request):
    data = json.loads(request.body)
    id = data.get("id")

    NomeTurma.objects.filter(id=id, escola=request.user.escola).delete()
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
            ano = data.get('ano')
            sala = data.get('sala')
            descricao = data.get('descricao', '')
            professor_id = data.get('professor_id')
            disciplina_id = data.get('disciplina_id')
            alunos_ids = data.get('alunos_ids', [])

            # -----------------------
            # Validação básica
            # -----------------------
            if not all([nome, turno, ano, sala, professor_id, disciplina_id]) or not alunos_ids:
                return JsonResponse({
                    'success': False,
                    'mensagem': 'Preencha todos os campos obrigatórios.'
                }, status=400)

            with transaction.atomic():

                # -----------------------
                # 1️⃣ Criar Turma
                # -----------------------
                turma = Turma.objects.create(
                    nome=nome,
                    turno=turno,
                    ano=ano,
                    sala=sala,
                    descricao=descricao,
                    escola=escola
                )

                # -----------------------
                # 2️⃣ Associar Alunos
                # -----------------------
                alunos = Aluno.objects.filter(
                    id__in=alunos_ids,
                    escola=escola,
                    ativo=True
                )
                turma.alunos.add(*alunos)

                # -----------------------
                # 3️⃣ Associar Professor + Disciplina
                # -----------------------
                TurmaDisciplina.objects.create(
                    turma=turma,
                    professor_id=professor_id,
                    disciplina_id=disciplina_id
                )

            return JsonResponse({
                'success': True,
                'mensagem': 'Turma criada com sucesso.'
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
