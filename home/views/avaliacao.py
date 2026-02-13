from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Prefetch
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
from datetime import date

from home.models import (
    Turma,
    Disciplina,
    Aluno,
    Avaliacao,
    Nota,
    TipoAvaliacao,
)


# =========================
# TIPOS DE AVALIAÇÃO
# =========================

def listar_tipos_avaliacao(request):
    pass

@login_required
def tipos_avaliacao(request):
    escola = request.user.escola

    if request.method == "POST":
        try:
            data = json.loads(request.body)

            nome = data.get("nome")
            peso = data.get("peso", 1)

            TipoAvaliacao.objects.create(
                nome=nome,
                peso=peso,
                escola=escola
            )

            return JsonResponse({"mensagem": "Tipo de avaliação criado com sucesso!"})

        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=400)

    tipos = TipoAvaliacao.objects.filter(escola=escola, ativo=True).order_by("nome")

    return render(request, "avaliacoes/tipos_avaliacao.html", {
        "tipos": tipos
    })

# =========================
# AVALIAÇÕES
# =========================

@login_required
def avaliacoes(request):

    escola = request.user.escola

    if request.method == "POST":
        try:
            data = json.loads(request.body)

            disciplina_id = data.get("disciplina_id")
            tipo_id = data.get("tipo_id")
            descricao = data.get("descricao")
            bimestre = data.get("bimestre")
            data_avaliacao = data.get("data") or date.today()

            # ================================
            # VALIDAÇÕES ANTI-QA
            # ================================

            if not disciplina_id:
                return JsonResponse({"erro": "Selecione a disciplina."}, status=400)

            if not tipo_id:
                return JsonResponse({"erro": "Selecione o tipo de avaliação."}, status=400)

            if not descricao or descricao.strip() == "":
                return JsonResponse({"erro": "Informe a descrição."}, status=400)

            if not bimestre or int(bimestre) not in [1, 2, 3, 4]:
                return JsonResponse({"erro": "Bimestre inválido (1 a 4)."}, status=400)

            if not data_avaliacao:
                return JsonResponse({"erro": "Informe a data da avaliação."}, status=400)
            
            # 🚫 Bloquear duplicidade
            if Avaliacao.objects.filter(
                escola=escola,
                disciplina_id=disciplina_id,
                bimestre=bimestre,
                descricao__iexact=descricao.strip()
            ).exists():
                return JsonResponse({
        "erro": "Já existe uma avaliação com essa descrição para essa disciplina e bimestre."}, status=400)

            Avaliacao.objects.create(
                disciplina_id=disciplina_id,
                tipo_id=tipo_id,
                descricao=descricao.strip(),
                bimestre=bimestre,
                data=data_avaliacao,
                escola=escola
            )

            return JsonResponse({"mensagem": "Avaliação criada com sucesso!"})

        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=400)

    disciplinas = Disciplina.objects.filter(escola=escola).order_by("nome")
    tipos = TipoAvaliacao.objects.filter(escola=escola, ativo=True).order_by("nome")

    avaliacoes_lista = Avaliacao.objects.filter(
        escola=escola
    ).select_related(
        "disciplina",
        "tipo"
    ).order_by("-data")

    return render(request, "avaliacoes/avaliacoes.html", {
        "disciplinas": disciplinas,
        "tipos": tipos,
        "avaliacoes": avaliacoes_lista
    })


@login_required
@require_http_methods(["DELETE"])
def excluir_avaliacao(request, avaliacao_id):

    escola = request.user.escola

    try:
        avaliacao = Avaliacao.objects.get(id=avaliacao_id, escola=escola)

        # 🚫 Se já houver notas, não pode excluir
        if avaliacao.notas.exists():
            return JsonResponse({
                "erro": "Não é possível excluir. Esta avaliação já possui notas lançadas."
            }, status=400)

        avaliacao.delete()

        return JsonResponse({"mensagem": "Avaliação excluída com sucesso."})

    except Avaliacao.DoesNotExist:
        return JsonResponse({"erro": "Avaliação não encontrada."}, status=404)
    

@login_required
def editar_avaliacao(request, avaliacao_id):

    escola = request.user.escola

    try:
        avaliacao = Avaliacao.objects.get(id=avaliacao_id, escola=escola)

        data = json.loads(request.body)

        avaliacao.disciplina_id = data.get("disciplina_id")
        avaliacao.tipo_id = data.get("tipo_id")
        avaliacao.descricao = data.get("descricao").strip()
        avaliacao.bimestre = data.get("bimestre")
        avaliacao.data = data.get("data")

        avaliacao.save()

        return JsonResponse({"mensagem": "Avaliação atualizada com sucesso!"})

    except Avaliacao.DoesNotExist:
        return JsonResponse({"erro": "Avaliação não encontrada."}, status=404)


# =========================
# LANÇAMENTO DE NOTAS
# =========================

@login_required
@require_http_methods(["GET", "POST"])
def lancar_notas(request):

    escola = request.user.escola

    # =========================================
    # POST — SALVAR NOTAS
    # =========================================
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            turma_id = data.get("turma_id")
            disciplina_id = data.get("disciplina_id")
            notas_recebidas = data.get("notas", {})

            for aluno_id, avaliacoes_dict in notas_recebidas.items():
                for avaliacao_id, valor in avaliacoes_dict.items():

                    if valor == "":
                        continue

                    avaliacao = Avaliacao.objects.get(
                        id=avaliacao_id,
                        escola=escola
                    )

                    aluno = Aluno.objects.get(
                        id=aluno_id,
                        escola=escola
                    )

                    Nota.objects.update_or_create(
                        aluno=aluno,
                        avaliacao=avaliacao,
                        escola=escola,
                        defaults={
                            "valor": valor
                        }
                    )

            return JsonResponse({"mensagem": "Notas salvas com sucesso!"})

        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=400)

    # =========================================
    # GET — CARREGAR TELA
    # =========================================

    turma_id = request.GET.get("turma")
    disciplina_id = request.GET.get("disciplina")

    turmas = Turma.objects.filter(escola=escola).order_by("nome")

    disciplinas = []
    alunos = []
    avaliacoes = []
    notas_dict = {}
    medias = {}

    if turma_id:
        disciplinas = Disciplina.objects.filter(
            turma__id=turma_id,
            escola=escola
        ).distinct()

    if turma_id and disciplina_id:

        alunos = Aluno.objects.filter(
            turma_principal_id=turma_id,
            escola=escola,
            ativo=True
        ).order_by("nome")

        avaliacoes = Avaliacao.objects.filter(
            turma_id=turma_id,
            disciplina_id=disciplina_id,
            escola=escola
        ).select_related("tipo").order_by("data")

        notas = Nota.objects.filter(
            avaliacao__in=avaliacoes,
            escola=escola
        ).select_related("aluno", "avaliacao")

        # Organiza notas em dicionário
        for nota in notas:
            aluno_id = nota.aluno.id
            avaliacao_id = nota.avaliacao.id

            if aluno_id not in notas_dict:
                notas_dict[aluno_id] = {}

            notas_dict[aluno_id][avaliacao_id] = nota.valor

        # =========================================
        # CÁLCULO DE MÉDIA
        # =========================================
        for aluno in alunos:
            soma = 0
            peso_total = 0

            for avaliacao in avaliacoes:
                nota_valor = notas_dict.get(aluno.id, {}).get(avaliacao.id)

                if nota_valor is not None:
                    peso = avaliacao.tipo.peso
                    soma += float(nota_valor) * float(peso)
                    peso_total += float(peso)

            if peso_total > 0:
                medias[aluno.id] = round(soma / peso_total, 2)
            else:
                medias[aluno.id] = None

    context = {
        "turmas": turmas,
        "disciplinas": disciplinas,
        "alunos": alunos,
        "avaliacoes": avaliacoes,
        "notas": notas_dict,
        "medias": medias,
        "turma_id": turma_id,
        "disciplina_id": disciplina_id,
    }

    return render(request, "avaliacoes/lancar_notas.html", context)


# =========================
# BOLETIM
# =========================

def boletim_aluno(request, aluno_id):
    pass
