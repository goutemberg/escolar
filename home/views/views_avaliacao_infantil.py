import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from home.models import ObservacaoInfantil
from django.http import HttpResponse
from django.template.loader import get_template
from django.http import HttpResponse

from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML


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

        todas_respostas = []
        todas_observacoes = []

        for av in dados.get("avaliacoes", []):
            aluno_id = av.get("aluno_id")

            # 🔥 AVALIAÇÃO (mantém simples)
            avaliacao, _ = AvaliacaoInfantil.objects.get_or_create(
                aluno_id=aluno_id,
                turma_id=turma_id,
                bimestre=bimestre,
                ano=ano
            )

            # 🔥 MONTA TODAS AS RESPOSTAS (SEM SALVAR AINDA)
            for item_id, valor in av.get("respostas", {}).items():

                todas_respostas.append({
                    "avaliacao_id": avaliacao.id,
                    "item_id": int(item_id),
                    "valor": valor
                })

            # 🔥 OBSERVAÇÃO
            texto = av.get("observacao", "")

            if texto:
                todas_observacoes.append({
                    "aluno_id": aluno_id,
                    "turma_id": turma_id,
                    "bimestre": bimestre,
                    "ano": ano,
                    "texto": texto,
                    "escola_id": request.user.escola.id
                })

        # =====================================================
        # 🔥 RESPOSTAS (BULK) — CORRIGIDO AQUI
        # =====================================================

        existentes = AvaliacaoResposta.objects.filter(
            avaliacao_id__in=[r["avaliacao_id"] for r in todas_respostas]
        )

        mapa_existentes = {
            (r.avaliacao_id, r.item_id): r
            for r in existentes
        }

        para_update = []
        para_create = []
        para_delete = []

        for r in todas_respostas:

            chave = (r["avaliacao_id"], r["item_id"])
            valor = r["valor"]

            # 🔥 SE FOR NULL → DELETE
            if valor is None:
                if chave in mapa_existentes:
                    para_delete.append(mapa_existentes[chave].id)
                continue

            # 🔥 UPDATE
            if chave in mapa_existentes:
                obj = mapa_existentes[chave]
                obj.valor = valor
                para_update.append(obj)

            # 🔥 CREATE
            else:
                para_create.append(
                    AvaliacaoResposta(
                        avaliacao_id=r["avaliacao_id"],
                        item_id=r["item_id"],
                        valor=valor
                    )
                )

        # 🔥 EXECUÇÃO EM LOTE
        if para_delete:
            AvaliacaoResposta.objects.filter(id__in=para_delete).delete()

        if para_create:
            AvaliacaoResposta.objects.bulk_create(para_create)

        if para_update:
            AvaliacaoResposta.objects.bulk_update(para_update, ["valor"])

        # =====================================================
        # 🔥 OBSERVAÇÕES (SEM ALTERAÇÃO)
        # =====================================================

        existentes_obs = ObservacaoInfantil.objects.filter(
            turma_id=turma_id,
            bimestre=bimestre,
            ano=ano
        )

        mapa_obs = {
            (o.aluno_id): o
            for o in existentes_obs
        }

        obs_update = []
        obs_create = []

        for o in todas_observacoes:

            if o["aluno_id"] in mapa_obs:
                obj = mapa_obs[o["aluno_id"]]
                obj.texto = o["texto"]
                obs_update.append(obj)
            else:
                obs_create.append(
                    ObservacaoInfantil(**o)
                )

        if obs_create:
            ObservacaoInfantil.objects.bulk_create(obs_create)

        if obs_update:
            ObservacaoInfantil.objects.bulk_update(obs_update, ["texto"])

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


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
        turma = Turma.objects.get(
            id=turma_id,
            escola=request.user.escola
        )

        # =====================================================
        # 🔥 CORREÇÃO: USAR RELAÇÃO MANY-TO-MANY (PADRÃO DO SISTEMA)
        # =====================================================
        alunos = (
            turma.alunos
            .filter(ativo=True)
            .distinct()
            .order_by("nome")
        )

        data = [
            {
                "id": a.id,
                "nome": a.nome
            }
            for a in alunos
        ]

        return JsonResponse({"alunos": data})

    except Turma.DoesNotExist:
        return JsonResponse({"erro": "Turma não encontrada"}, status=404)

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

        # =========================
        # 🔥 NOVO: BUSCAR OBSERVAÇÕES
        # =========================
        from home.models import ObservacaoInfantil

        observacoes_qs = ObservacaoInfantil.objects.filter(
            turma_id=turma_id,
            bimestre=bimestre,
            ano=ano,
            aluno__escola=request.user.escola
        )

        observacoes_dict = {
            o.aluno_id: o.texto for o in observacoes_qs
        }

        return JsonResponse({
            "avaliacoes": resposta_dict,
            "observacoes": observacoes_dict  # 🔥 NOVO
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

    # =========================
    # OBSERVAÇÕES POR PERÍODO
    # =========================
    observacoes_por_periodo = {}

    observacoes = ObservacaoInfantil.objects.filter(
        aluno=aluno,
        turma=turma,
        escola=request.user.escola
    )

    for obs in observacoes:
        chave = f"{obs.bimestre}/{obs.ano}"
        observacoes_por_periodo[chave] = obs.texto

    return render(request, "pages/boletim_infantil.html", {
        "aluno": aluno,
        "turma": turma,
        "dados": dados,
        "observacoes": observacoes_por_periodo 
    })


@csrf_exempt
@login_required
def salvar_observacao_infantil(request):

    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)

    try:
        data = json.loads(request.body)

        aluno_id = data.get("aluno_id")
        turma_id = data.get("turma_id")
        bimestre = data.get("bimestre")
        texto = data.get("texto")

        ano = datetime.now().year

        observacao, _ = ObservacaoInfantil.objects.update_or_create(
            aluno_id=aluno_id,
            turma_id=turma_id,
            bimestre=bimestre,
            ano=ano,
            defaults={
                "texto": texto,
                "escola": request.user.escola
            }
        )

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


@login_required
def boletim_infantil_pdf(request, aluno_id, turma_id):

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

    # 🔥 OBSERVAÇÃO
    observacoes = ObservacaoInfantil.objects.filter(
        aluno=aluno,
        turma=turma,
        escola=request.user.escola
    )

    observacoes_dict = {
        f"{o.bimestre}/{o.ano}": o.texto for o in observacoes
    }

    html_string = render_to_string(
        "pages/boletim_infantil.html",
        {
            "aluno": aluno,
            "turma": turma,
            "dados": dados,
            "observacoes": observacoes_dict,
            "user": request.user

        }
    )

    html = HTML(string=html_string)
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="boletim_{aluno.id}.pdf"'

    return response