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
    escola = request.user.escola

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
    escola = request.user.escola
    user = request.user

    # =========================================
    # POST — SALVAR NOTAS / CONCEITOS
    # =========================================
    if request.method == "POST":
        # JSON
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido."}, status=400)

        turma_id = data.get("turma_id")
        disciplina_id = data.get("disciplina_id")
        notas_recebidas = data.get("notas", {})

        # obrigatórios
        if not turma_id or not disciplina_id:
            return JsonResponse({"erro": "turma_id e disciplina_id são obrigatórios."}, status=400)

        if not isinstance(notas_recebidas, dict):
            return JsonResponse({"erro": "Formato inválido: notas deve ser um dicionário."}, status=400)

        # Turma / Disciplina da escola
        try:
            turma = Turma.objects.get(id=turma_id, escola=escola)
        except Turma.DoesNotExist:
            return JsonResponse({"erro": "Turma inválida."}, status=404)

        try:
            disciplina = Disciplina.objects.get(id=disciplina_id, escola=escola)
        except Disciplina.DoesNotExist:
            return JsonResponse({"erro": "Disciplina inválida."}, status=404)

        # Disciplina precisa estar vinculada à turma (evita salvar em turma errada)
        vinculo_ok = TurmaDisciplina.objects.filter(
            turma=turma,
            disciplina=disciplina,
            escola=escola
        ).exists()

        if not vinculo_ok:
            return JsonResponse({"erro": "Disciplina não vinculada a esta turma."}, status=403)

        # Se professor, opcionalmente validar se ele leciona essa turma/disciplina
        if getattr(user, "role", None) == "professor":
            prof = Docente.objects.filter(user=user, escola=escola).first()
            if not prof:
                return JsonResponse({"erro": "Professor inválido."}, status=403)

            permitido = TurmaDisciplina.objects.filter(
                turma=turma,
                disciplina=disciplina,
                professor=prof,
                escola=escola
            ).exists()
            if not permitido:
                return JsonResponse({"erro": "Você não está vinculado a esta turma/disciplina."}, status=403)

        sistema = getattr(turma, "sistema_avaliacao", "NUM")  # NUM ou CON

        # avaliações permitidas nesse contexto
        avaliacoes_qs = Avaliacao.objects.filter(
            turma_id=turma.id,
            disciplina_id=disciplina.id,
            escola=escola
        ).values_list("id", flat=True)

        avaliacoes_validas = set(map(int, avaliacoes_qs))

        erros = []

        try:
            with transaction.atomic():
                for aluno_id_str, avaliacoes_dict in notas_recebidas.items():

                    # aluno_id
                    try:
                        aluno_id = int(aluno_id_str)
                    except (TypeError, ValueError):
                        erros.append({"aluno_id": aluno_id_str, "mensagem": "aluno_id inválido"})
                        continue

                    if not isinstance(avaliacoes_dict, dict):
                        erros.append({"aluno_id": aluno_id, "mensagem": "Formato inválido de avaliações"})
                        continue

                    # aluno da escola e da turma (turma_principal)
                    aluno = Aluno.objects.filter(
                        id=aluno_id,
                        escola=escola,
                        ativo=True,
                        turma_principal_id=turma.id
                    ).first()

                    if not aluno:
                        erros.append({"aluno_id": aluno_id, "mensagem": "Aluno inválido/fora da turma"})
                        continue

                    for avaliacao_id_str, valor_raw in avaliacoes_dict.items():
                        # avaliacao_id
                        try:
                            avaliacao_id = int(avaliacao_id_str)
                        except (TypeError, ValueError):
                            erros.append({"aluno_id": aluno_id, "avaliacao_id": avaliacao_id_str, "mensagem": "avaliacao_id inválido"})
                            continue

                        if avaliacao_id not in avaliacoes_validas:
                            erros.append({"aluno_id": aluno_id, "avaliacao_id": avaliacao_id, "mensagem": "Avaliação não pertence ao contexto"})
                            continue

                        # vazio -> ignora (não grava nada)
                        if valor_raw is None or str(valor_raw).strip() == "":
                            continue

                        # carrega avaliação (já garantida)
                        avaliacao = Avaliacao.objects.get(id=avaliacao_id, escola=escola)

                        if sistema == "NUM":
                            dec = _to_decimal(valor_raw)
                            if dec is None:
                                erros.append({"aluno_id": aluno_id, "avaliacao_id": avaliacao_id, "mensagem": "Nota inválida"})
                                continue

                            Nota.objects.update_or_create(
                                aluno=aluno,
                                avaliacao=avaliacao,
                                escola=escola,
                                defaults={
                                    "valor": dec,
                                    "conceito": None,
                                }
                            )

                        else:  # CON
                            conceito = str(valor_raw).strip().upper()

                            # aceita texto completo também (pra ser tolerante)
                            mapa = {
                                "E": "E",
                                "EVOLUCAO": "E",
                                "EVOLUÇÃO": "E",
                                "O": "O",
                                "OTIMO": "O",
                                "ÓTIMO": "O",
                                "B": "B",
                                "BOM": "B",
                            }
                            conceito = mapa.get(conceito, conceito)

                            if conceito not in CONCEITOS_VALIDOS:
                                erros.append({"aluno_id": aluno_id, "avaliacao_id": avaliacao_id, "mensagem": "Conceito inválido (use E/O/B)"})
                                continue

                            Nota.objects.update_or_create(
                                aluno=aluno,
                                avaliacao=avaliacao,
                                escola=escola,
                                defaults={
                                    "valor": None,
                                    "conceito": conceito,
                                }
                            )

        except Exception as e:
            return JsonResponse({"erro": f"Falha ao salvar: {str(e)}"}, status=400)

        if erros:
            # 207 (parcial) é legal, mas pode manter 200 com flag
            return JsonResponse({"status": "parcial", "mensagem": "Alguns lançamentos falharam.", "erros": erros}, status=207)

        return JsonResponse({"status": "sucesso", "mensagem": "Lançamentos salvos com sucesso!"})

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

            # disciplinas vinculadas à turma (via TurmaDisciplina)
            disciplinas = Disciplina.objects.filter(
                turmadisciplina__turma=turma,
                turmadisciplina__escola=escola,
                escola=escola
            ).distinct().order_by("nome")

    if turma and disciplina_id:
        disciplina = Disciplina.objects.filter(id=disciplina_id, escola=escola).first()

    if turma and disciplina:
        # alunos da turma
        alunos = Aluno.objects.filter(
            turma_principal_id=turma.id,
            escola=escola,
            ativo=True
        ).order_by("nome")

        avaliacoes = Avaliacao.objects.filter(
            turma_id=turma.id,
            disciplina_id=disciplina.id,
            escola=escola
        ).select_related("tipo").order_by("data")

        notas = Nota.objects.filter(
            avaliacao__in=avaliacoes,
            aluno__in=alunos,
            escola=escola
        ).select_related("aluno", "avaliacao", "avaliacao__tipo")

        # Organiza notas em dicionário
        for nota in notas:
            aid = nota.aluno_id
            avid = nota.avaliacao_id
            if aid not in notas_dict:
                notas_dict[aid] = {}

            if turma_sistema_avaliacao == "CON":
                notas_dict[aid][avid] = nota.conceito  # E/O/B
            else:
                notas_dict[aid][avid] = str(nota.valor) if nota.valor is not None else None

        # média só se NUM
        if turma_sistema_avaliacao == "NUM":
            for aluno in alunos:
                soma = Decimal("0")
                peso_total = Decimal("0")

                for avaliacao in avaliacoes:
                    nv = notas_dict.get(aluno.id, {}).get(avaliacao.id)

                    if nv is not None and str(nv).strip() != "":
                        dec = _to_decimal(nv)
                        if dec is None:
                            continue
                        peso = Decimal(str(avaliacao.tipo.peso))
                        soma += dec * peso
                        peso_total += peso

                medias[aluno.id] = (soma / peso_total).quantize(Decimal("0.01")) if peso_total > 0 else None
        else:
            for aluno in alunos:
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
        "turma_sistema_avaliacao": turma_sistema_avaliacao,  # ✅ chave pro front
    }

    return render(request, "avaliacoes/lancar_notas.html", context)


# =========================
# BOLETIM
# =========================

@login_required
def boletim_aluno(request, aluno_id):

    escola = request.user.escola

    aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)

    # Buscar todas disciplinas da escola
    disciplinas = Disciplina.objects.filter(escola=escola)

    boletim = []

    for disciplina in disciplinas:

        avaliacoes = Avaliacao.objects.filter(
            escola=escola,
            disciplina=disciplina
        ).select_related("tipo")

        notas = Nota.objects.filter(
            escola=escola,
            aluno=aluno,
            avaliacao__disciplina=disciplina
        ).select_related("avaliacao", "avaliacao__tipo")

        # Organizar por bimestre
        bimestres = {
            1: [],
            2: [],
            3: [],
            4: []
        }

        for nota in notas:
            bimestres[nota.avaliacao.bimestre].append(nota)

        medias_bimestre = {}

        for bimestre, lista_notas in bimestres.items():

            if not lista_notas:
                medias_bimestre[bimestre] = None
                continue

            soma = Decimal(0)
            soma_peso = Decimal(0)
            nota_recuperacao = None

            for nota in lista_notas:

                peso = nota.avaliacao.tipo.peso or Decimal(1)

                # Se for recuperação
                if nota.avaliacao.tipo.nome.lower() == "recuperação":
                    nota_recuperacao = nota.valor
                    continue

                soma += nota.valor * peso
                soma_peso += peso

            if soma_peso > 0:
                media = soma / soma_peso
            else:
                media = None

            # Aplicar regra da recuperação
            if nota_recuperacao is not None:
                if media is None:
                    media_final = nota_recuperacao
                else:
                    media_final = max(media, nota_recuperacao)
            else:
                media_final = media

            medias_bimestre[bimestre] = (
                round(media_final, 2) if media_final is not None else None
            )

        # Média final anual
        notas_validas = [
            m for m in medias_bimestre.values() if m is not None
        ]

        if notas_validas:
            media_final = round(
                sum(notas_validas) / len(notas_validas), 2
            )
        else:
            media_final = None

        situacao = (
            "Aprovado"
            if media_final is not None and media_final >= 7
            else "Reprovado"
        )

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
