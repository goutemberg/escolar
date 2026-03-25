from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Prefetch
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
from datetime import date, datetime
from collections import defaultdict
from decimal import Decimal
from django.db import transaction
from decimal import Decimal, InvalidOperation

from home.models import (
    Turma,
    Disciplina,
    Aluno,
    Avaliacao,
    Nota,
    TipoAvaliacao,
    TurmaDisciplina,
    Docente,
)


# =========================
# TIPOS DE AVALIAÇÃO
# =========================

def listar_tipos_avaliacao(request):
    pass


@login_required
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def tipos_avaliacao(request):
    escola = request.escola


    # =========================
    # GET: listar
    # =========================
    if request.method == "GET":
        tipos = TipoAvaliacao.objects.filter(escola=escola, ativo=True).order_by("nome")
        return render(request, "avaliacoes/tipos_avaliacao.html", {"tipos": tipos})

    # =========================
    # JSON body (POST/PUT/DELETE)
    # =========================
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    # normaliza
    def _peso_to_float(v):
        try:
            return float(str(v).replace(",", "."))
        except Exception:
            return None

    # =========================
    # POST: criar
    # =========================
    if request.method == "POST":
        nome = (data.get("nome") or "").strip()
        peso = _peso_to_float(data.get("peso", 1))

        if not nome:
            return JsonResponse({"erro": "Nome é obrigatório."}, status=400)
        if peso is None:
            return JsonResponse({"erro": "Peso inválido."}, status=400)

        TipoAvaliacao.objects.create(
            nome=nome,
            peso=peso,
            escola=escola,
            ativo=True
        )
        return JsonResponse({"mensagem": "Tipo de avaliação criado com sucesso!"})

    # =========================
    # PUT: editar
    # =========================
    if request.method == "PUT":
        tipo_id = data.get("id")
        nome = (data.get("nome") or "").strip()
        peso = _peso_to_float(data.get("peso"))

        if not tipo_id:
            return JsonResponse({"erro": "ID é obrigatório."}, status=400)
        if not nome:
            return JsonResponse({"erro": "Nome é obrigatório."}, status=400)
        if peso is None:
            return JsonResponse({"erro": "Peso inválido."}, status=400)

        tipo = get_object_or_404(TipoAvaliacao, id=tipo_id, escola=escola)
        tipo.nome = nome
        tipo.peso = peso
        if hasattr(tipo, "ativo") and tipo.ativo is False:
            tipo.ativo = True  # caso esteja reativando sem querer
        tipo.save()

        return JsonResponse({"mensagem": "Tipo de avaliação atualizado com sucesso!"})

    # =========================
    # DELETE: excluir (soft delete)
    # =========================
    if request.method == "DELETE":
        tipo_id = data.get("id")
        if not tipo_id:
            return JsonResponse({"erro": "ID é obrigatório."}, status=400)

        tipo = get_object_or_404(TipoAvaliacao, id=tipo_id, escola=escola)

        # soft delete
        if hasattr(tipo, "ativo"):
            tipo.ativo = False
            tipo.save(update_fields=["ativo"])
        else:
            # fallback: delete real se não existir 'ativo'
            tipo.delete()

        return JsonResponse({"mensagem": "Tipo de avaliação excluído com sucesso!"})

    return JsonResponse({"erro": "Método não suportado."}, status=405)
# =========================
# AVALIAÇÕES
# =========================

@login_required
def avaliacoes(request):

    escola = request.escola


    # =========================================
    # POST — CRIAR AVALIAÇÃO(S)
    # =========================================
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            turma_id = data.get("turma_id")
            disciplina_id = data.get("disciplina_id")
            tipo_id = data.get("tipo_id")
            descricao = (data.get("descricao") or "").strip()
            bimestre = data.get("bimestre")
            quantidade = int(data.get("quantidade") or 1)
            data_avaliacao = data.get("data") or date.today()

            # ================================
            # VALIDAÇÕES
            # ================================

            if not turma_id:
                return JsonResponse({"erro": "Selecione a turma."}, status=400)

            if not disciplina_id:
                return JsonResponse({"erro": "Selecione a disciplina."}, status=400)

            if not tipo_id:
                return JsonResponse({"erro": "Selecione o tipo de avaliação."}, status=400)

            if not descricao:
                return JsonResponse({"erro": "Informe a descrição."}, status=400)

            if not bimestre or int(bimestre) not in [1, 2, 3, 4]:
                return JsonResponse({"erro": "Bimestre inválido (1 a 4)."}, status=400)

            if quantidade < 1:
                return JsonResponse({"erro": "Quantidade deve ser pelo menos 1."}, status=400)

            # valida turma/disciplinas da escola
            turma = Turma.objects.filter(id=turma_id, escola=escola).first()
            if not turma:
                return JsonResponse({"erro": "Turma inválida."}, status=404)

            disciplina = Disciplina.objects.filter(id=disciplina_id, escola=escola).first()
            if not disciplina:
                return JsonResponse({"erro": "Disciplina inválida."}, status=404)

            tipo = TipoAvaliacao.objects.filter(id=tipo_id, escola=escola).first()
            if not tipo:
                return JsonResponse({"erro": "Tipo inválido."}, status=404)

            criadas = []

            with transaction.atomic():

                for i in range(1, quantidade + 1):

                    # nome automático
                    desc_final = descricao if quantidade == 1 else f"{descricao} {i}"

                    # 🚫 evitar duplicidade
                    existe = Avaliacao.objects.filter(
                        escola=escola,
                        turma=turma,
                        disciplina=disciplina,
                        bimestre=bimestre,
                        descricao__iexact=desc_final
                    ).exists()

                    if existe:
                        continue

                    avaliacao = Avaliacao.objects.create(
                        turma=turma,
                        disciplina=disciplina,
                        tipo=tipo,
                        descricao=desc_final,
                        bimestre=bimestre,
                        data=data_avaliacao,
                        escola=escola
                    )

                    criadas.append(avaliacao.id)

            if not criadas:
                return JsonResponse({
                    "erro": "Nenhuma avaliação foi criada (todas já existiam)."
                }, status=400)

            return JsonResponse({
                "mensagem": f"{len(criadas)} avaliação(ões) criada(s) com sucesso!"
            })

        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=400)

    # =========================================
    # GET — CARREGAR TELA
    # =========================================

    turmas = Turma.objects.filter(escola=escola).order_by("nome")

    disciplinas = Disciplina.objects.filter(
        escola=escola
    ).order_by("nome")

    tipos = TipoAvaliacao.objects.filter(
        escola=escola,
        ativo=True
    ).order_by("nome")

    avaliacoes_lista = Avaliacao.objects.filter(
        escola=escola
    ).select_related(
        "turma",
        "disciplina",
        "tipo"
    ).order_by("-data")

    return render(request, "avaliacoes/avaliacoes.html", {
        "turmas": turmas,
        "disciplinas": disciplinas,
        "tipos": tipos,
        "avaliacoes": avaliacoes_lista
    })


@login_required
@require_http_methods(["DELETE"])
def excluir_avaliacao(request, avaliacao_id):

    escola = request.escola


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

    escola = request.escola


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

CONCEITOS_VALIDOS = {"E", "O", "B"}  # Evolução, Ótimo, Bom


def _to_decimal(valor):
    """
    Converte string/num para Decimal.
    Aceita vírgula.
    Retorna Decimal ou None.
    """
    if valor is None:
        return None
    if isinstance(valor, (int, float, Decimal)):
        try:
            return Decimal(str(valor))
        except Exception:
            return None
    s = str(valor).strip()
    if s == "":
        return None
    s = s.replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


@login_required
@require_http_methods(["GET", "POST"])
def lancar_notas(request):
    escola = request.escola

    user = request.user

    # =========================================
    # POST — SALVAR NOTAS
    # =========================================
    if request.method == "POST":
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido."}, status=400)

        turma_id = data.get("turma_id")
        disciplina_id = data.get("disciplina_id")
        notas_recebidas = data.get("notas", {})

        if not turma_id or not disciplina_id:
            return JsonResponse({"erro": "turma_id e disciplina_id são obrigatórios."}, status=400)

        try:
            turma = Turma.objects.get(id=turma_id, escola=escola)
        except Turma.DoesNotExist:
            return JsonResponse({"erro": "Turma inválida."}, status=404)

        try:
            disciplina = Disciplina.objects.get(id=disciplina_id, escola=escola)
        except Disciplina.DoesNotExist:
            return JsonResponse({"erro": "Disciplina inválida."}, status=404)

        sistema = getattr(turma, "sistema_avaliacao", "NUM")

        avaliacoes = Avaliacao.objects.filter(
            turma=turma,
            disciplina=disciplina,
            escola=escola
        )

        avaliacoes_validas = set(avaliacoes.values_list("id", flat=True))

        try:
            with transaction.atomic():
                for aluno_id_str, aval_dict in notas_recebidas.items():

                    aluno = Aluno.objects.filter(
                        id=int(aluno_id_str),
                        turma_principal=turma,
                        escola=escola,
                        ativo=True
                    ).first()

                    if not aluno:
                        continue

                    for avaliacao_id_str, valor in aval_dict.items():

                        avaliacao_id = int(avaliacao_id_str)

                        if avaliacao_id not in avaliacoes_validas:
                            continue

                        if valor in [None, ""]:
                            continue

                        avaliacao = Avaliacao.objects.get(id=avaliacao_id)

                        if sistema == "NUM":
                            dec = _to_decimal(valor)
                            if dec is None:
                                continue

                            Nota.objects.update_or_create(
                                aluno=aluno,
                                avaliacao=avaliacao,
                                escola=escola,
                                defaults={"valor": dec, "conceito": None}
                            )
                        else:
                            Nota.objects.update_or_create(
                                aluno=aluno,
                                avaliacao=avaliacao,
                                escola=escola,
                                defaults={"valor": None, "conceito": valor}
                            )

        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=400)

        return JsonResponse({"mensagem": "Notas salvas com sucesso!"})

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
    turma_sistema_avaliacao = None

    turma = None
    disciplina = None

    if turma_id:
        turma = Turma.objects.filter(id=turma_id, escola=escola).first()

        if turma:
            turma_sistema_avaliacao = getattr(turma, "sistema_avaliacao", "NUM")

            disciplinas = Disciplina.objects.filter(
                turmadisciplina__turma=turma,
                turmadisciplina__escola=escola,
                escola=escola
            ).distinct().order_by("nome")

    if turma and disciplina_id:
        disciplina = Disciplina.objects.filter(id=disciplina_id, escola=escola).first()

    if turma and disciplina:

        alunos = Aluno.objects.filter(
            turma_principal=turma,
            escola=escola,
            ativo=True
        ).order_by("nome")

        avaliacoes = Avaliacao.objects.filter(
            escola=escola,
            turma=turma,
            disciplina=disciplina
        ).select_related("tipo").order_by("bimestre", "descricao")

        notas = Nota.objects.filter(
            avaliacao__in=avaliacoes,
            aluno__in=alunos,
            escola=escola
        ).select_related("aluno", "avaliacao", "avaliacao__tipo")

        for nota in notas:
            aid = nota.aluno_id
            avid = nota.avaliacao_id

            if aid not in notas_dict:
                notas_dict[aid] = {}

            if turma_sistema_avaliacao == "CON":
                notas_dict[aid][avid] = nota.conceito
            else:
                notas_dict[aid][avid] = str(nota.valor) if nota.valor is not None else None

        if turma_sistema_avaliacao == "NUM":
            for aluno in alunos:
                soma = Decimal("0")
                peso_total = Decimal("0")

                for avaliacao in avaliacoes:
                    nv = notas_dict.get(aluno.id, {}).get(avaliacao.id)

                    if nv not in [None, ""]:
                        dec = _to_decimal(nv)
                        if dec is None:
                            continue

                        peso = Decimal(str(avaliacao.tipo.peso))
                        soma += dec * peso
                        peso_total += peso

                medias[aluno.id] = (soma / peso_total).quantize(Decimal("0.01")) if peso_total > 0 else None

    context = {
        "turmas": turmas,
        "disciplinas": disciplinas,
        "alunos": alunos,
        "avaliacoes": avaliacoes,
        "notas": notas_dict,
        "medias": medias,
        "turma_id": turma_id,
        "disciplina_id": disciplina_id,
        "turma_sistema_avaliacao": turma_sistema_avaliacao,
    }

    return render(request, "avaliacoes/lancar_notas.html", context)


# =========================
# BOLETIM
# =========================

@login_required
def boletim_aluno(request, aluno_id):

    escola = request.escola

    aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)

    turma = aluno.turma_principal

    disciplinas = Disciplina.objects.filter(
        turmadisciplina__turma=turma,
        turmadisciplina__escola=escola,
        escola=escola
    ).distinct()

    boletim = []

    for disciplina in disciplinas:

        avaliacoes = Avaliacao.objects.filter(
            escola=escola,
            disciplina=disciplina,
            turma=turma
        ).select_related("tipo")

        notas = Nota.objects.filter(
            escola=escola,
            aluno=aluno,
            avaliacao__in=avaliacoes
        ).select_related("avaliacao", "avaliacao__tipo")

        bimestres = {1: [], 2: [], 3: [], 4: []}

        for nota in notas:
            bimestres[nota.avaliacao.bimestre].append(nota)

        medias_bimestre = {}

        for bimestre, lista in bimestres.items():

            if not lista:
                medias_bimestre[bimestre] = None
                continue

            soma = Decimal(0)
            peso_total = Decimal(0)
            rec = None

            for nota in lista:
                peso = nota.avaliacao.tipo.peso or Decimal(1)

                if nota.avaliacao.tipo.nome.lower() == "recuperação":
                    rec = nota.valor
                    continue

                soma += nota.valor * peso
                peso_total += peso

            media = (soma / peso_total) if peso_total > 0 else None

            if rec is not None:
                media_final = max(media, rec) if media else rec
            else:
                media_final = media

            medias_bimestre[bimestre] = round(media_final, 2) if media_final else None

        notas_validas = [m for m in medias_bimestre.values() if m is not None]

        media_final = round(sum(notas_validas) / len(notas_validas), 2) if notas_validas else None

        situacao = "Aprovado" if media_final and media_final >= 7 else "Reprovado"

        boletim.append({
            "disciplina": disciplina.nome,
            "bimestres": medias_bimestre,
            "media_final": media_final,
            "situacao": situacao
        })

    context = {
        "escola": escola,
        "aluno": aluno,
        "boletim": boletim,
        "ano": datetime.now().year
    }

    return render(request, "avaliacoes/boletim_aluno.html", context)