import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

from home.models import (
    AvaliacaoInfantil,
    AvaliacaoResposta,
    AvaliacaoItem,
    Aluno,
    Turma,
    AvaliacaoCategoria,
)


@csrf_exempt
@login_required
def salvar_avaliacao_infantil(request):

    if request.method != "POST":
        return JsonResponse({"erro": "Método não permitido"}, status=405)

    try:
        dados = json.loads(request.body)

        turma_id = dados.get("turma_id")
        bimestre = dados.get("bimestre")
        ano = datetime.now().year

        for av in dados.get("avaliacoes", []):
            aluno_id = av.get("aluno_id")

            avaliacao, _ = AvaliacaoInfantil.objects.get_or_create(
                aluno_id=aluno_id,
                turma_id=turma_id,
                bimestre=bimestre,
                ano=ano
            )

            for item_id, valor in av.get("respostas", {}).items():

                AvaliacaoResposta.objects.update_or_create(
                    avaliacao=avaliacao,
                    item_id=int(item_id),
                    defaults={"valor": valor}
                )

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)



import json

@login_required
def tela_avaliacao_infantil(request):

    itens_qs = AvaliacaoItem.objects.filter(
        escola=request.user.escola,
        ativo=True
    ).select_related('categoria').order_by('categoria__ordem', 'ordem')

    itens = [
        {
            "id": i.id,
            "descricao": i.descricao,
            "categoria_id": i.categoria.id,
            "categoria_nome": i.categoria.nome
        }
        for i in itens_qs
    ]

    return render(request, "pages/avaliacao_infantil.html", {
        "itens": json.dumps(itens) 
    })


@login_required
def buscar_alunos_por_turma(request):

    turma_id = request.GET.get("turma_id")

    if not turma_id:
        return JsonResponse({"erro": "Turma não informada"}, status=400)

    try:
        alunos = Aluno.objects.filter(
            turma_principal_id=turma_id,
            escola=request.user.escola,
            ativo=True
        ).order_by("nome")

        data = [
            {
                "id": a.id,
                "nome": a.nome
            }
            for a in alunos
        ]

        return JsonResponse({"alunos": data})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@login_required
def buscar_avaliacoes_infantil(request):

    turma_id = request.GET.get("turma_id")
    bimestre = request.GET.get("bimestre")
    ano = datetime.now().year

    if not turma_id or not bimestre:
        return JsonResponse({"erro": "Dados inválidos"}, status=400)

    try:
        avaliacoes = AvaliacaoInfantil.objects.filter(
            turma_id=turma_id,
            bimestre=bimestre,
            ano=ano,
            aluno__escola=request.user.escola
        )

        resposta_dict = {}

        respostas = AvaliacaoResposta.objects.filter(
            avaliacao__in=avaliacoes
        ).select_related('avaliacao', 'item')

        for r in respostas:
            aluno_id = r.avaliacao.aluno_id

            if aluno_id not in resposta_dict:
                resposta_dict[aluno_id] = {}

            resposta_dict[aluno_id][r.item_id] = r.valor

        return JsonResponse({
            "avaliacoes": resposta_dict
        })

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@login_required
def buscar_turmas(request):

    try:
        turmas = Turma.objects.filter(
            escola=request.user.escola,
            status="ATIVA",
            sistema_avaliacao="CON"
        ).order_by("nome")

        data = [
            {
                "id": t.id,
                "nome": t.nome
            }
            for t in turmas
        ]

        return JsonResponse({"turmas": data})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@login_required
def configuracao_avaliacao_infantil(request):

    escola = request.user.escola

    categorias = AvaliacaoCategoria.objects.filter(
        escola=escola
    ).prefetch_related('itens').order_by('ordem')

    return render(request, "pages/config_avaliacao_infantil.html", {
        "categorias": categorias
    })


@csrf_exempt
@login_required
def salvar_item_avaliacao(request):

    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)

    try:
        data = json.loads(request.body)

        categoria_id = data.get("categoria_id")
        descricao = data.get("descricao")

        AvaliacaoItem.objects.create(
            categoria_id=categoria_id,
            descricao=descricao,
            escola=request.user.escola,
            ativo=True
        )

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)
    

@csrf_exempt
@login_required
def salvar_categoria(request):

    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)

    try:
        data = json.loads(request.body)

        nome = data.get("nome")

        AvaliacaoCategoria.objects.create(
            nome=nome,
            escola=request.user.escola
        )

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@csrf_exempt
@login_required
def editar_categoria(request, id):

    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)

    try:
        data = json.loads(request.body)
        nome = data.get("nome")

        categoria = AvaliacaoCategoria.objects.get(
            id=id,
            escola=request.user.escola
        )

        categoria.nome = nome
        categoria.save()

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@login_required
def excluir_categoria(request, id):

    try:
        categoria = AvaliacaoCategoria.objects.get(
            id=id,
            escola=request.user.escola
        )

        categoria.delete()

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@csrf_exempt
@login_required
def editar_item(request, id):

    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)

    try:
        data = json.loads(request.body)
        descricao = data.get("descricao")

        item = AvaliacaoItem.objects.get(
            id=id,
            escola=request.user.escola
        )

        item.descricao = descricao
        item.save()

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@login_required
def excluir_item(request, id):

    try:
        item = AvaliacaoItem.objects.get(
            id=id,
            escola=request.user.escola
        )

        item.delete()

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@csrf_exempt
@login_required
def salvar_ordem(request):

    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)

    try:
        data = json.loads(request.body)

        categorias = data.get("categorias", [])

        for cat_index, cat in enumerate(categorias):

            categoria = AvaliacaoCategoria.objects.get(
                id=cat["id"],
                escola=request.user.escola
            )

            categoria.ordem = cat_index
            categoria.save()

            for item_index, item_id in enumerate(cat["itens"]):

                item = AvaliacaoItem.objects.get(
                    id=item_id,
                    escola=request.user.escola
                )

                item.ordem = item_index
                item.save()

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@login_required
def boletim_infantil(request, aluno_id, turma_id):

    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=request.user.escola
    )

    turma = get_object_or_404(
        Turma,
        id=turma_id,
        escola=request.user.escola
    )

    # 🔥 AGORA FILTRA POR ALUNO + TURMA
    avaliacoes = AvaliacaoInfantil.objects.filter(
        aluno=aluno,
        turma=turma
    ).order_by('-ano', '-bimestre')

    respostas = AvaliacaoResposta.objects.filter(
        avaliacao__in=avaliacoes
    ).select_related('item__categoria', 'avaliacao')

    dados = {}

    for r in respostas:
        chave = f"{r.avaliacao.bimestre}/{r.avaliacao.ano}"

        if chave not in dados:
            dados[chave] = {}

        categoria = r.item.categoria.nome

        if categoria not in dados[chave]:
            dados[chave][categoria] = []

        dados[chave][categoria].append({
            "descricao": r.item.descricao,
            "valor": r.valor
        })

    return render(request, "pages/boletim_infantil.html", {
        "aluno": aluno,
        "turma": turma,  # 🔥 agora é a correta
        "dados": dados
    })