import json

from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import re

from home.models import (
    Aluno,
    Turma,
    Saude,
    TransporteEscolar,
    Autorizacoes
)

from home.utils import gerar_matricula_unica


@login_required
@require_GET
def preview_matricula(request):
    """
    Preview de matrícula em lote.
    Usa a MESMA lógica do cadastro individual,
    apenas simulando a sequência.
    """
    quantidade = int(request.GET.get("quantidade", 1))

    # Matrícula base (ex: ALU20250001)
    base = gerar_matricula_unica()

    match = re.search(r"(\D+)(\d+)$", base)
    if not match:
        return JsonResponse(
            {"error": "Formato de matrícula inválido"},
            status=400
        )

    prefixo = match.group(1)   # ALU2025
    inicio = int(match.group(2))  # 0001

    matriculas = [
        f"{prefixo}{str(inicio + i).zfill(len(match.group(2)))}"
        for i in range(quantidade)
    ]

    return JsonResponse({"matriculas": matriculas})


@login_required
@require_POST
def salvar_matricula_lote(request):
    """
    Salva alunos em lote (irmãos),
    reutilizando os mesmos models da matrícula individual.
    Cada aluno é tratado de forma isolada (atomic por aluno).
    """

    # =========================
    # JSON
    # =========================
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "erro", "mensagem": "JSON inválido"},
            status=400
        )

    alunos_data = data.get("alunos", [])

    if not alunos_data or len(alunos_data) < 2:
        return JsonResponse(
            {"status": "erro", "mensagem": "Informe pelo menos dois alunos"},
            status=400
        )

    escola = getattr(request.user, "escola", None)
    if not escola:
        return JsonResponse(
            {"status": "erro", "mensagem": "Usuário sem escola associada"},
            status=403
        )

    alunos_criados = []
    erros = []

    # =========================
    # PROCESSAMENTO POR ALUNO
    # =========================
    for index, aluno_data in enumerate(alunos_data, start=1):
        try:
            with transaction.atomic():

                cpf = aluno_data.get("cpf")

                # Regra explícita (melhor que erro de banco)
                if cpf and Aluno.objects.filter(cpf=cpf, escola=escola).exists():
                    raise ValueError("CPF já cadastrado para esta escola")

                # =========================
                # ALUNO
                # =========================
                aluno = Aluno.objects.create(
                    nome=aluno_data.get("nome", "").strip(),
                    data_nascimento=aluno_data.get("data_nascimento") or None,
                    cpf=cpf,
                    rg=aluno_data.get("rg"),
                    sexo=aluno_data.get("sexo", ""),
                    tipo_sanguineo=aluno_data.get("tipo_sanguineo", ""),
                    forma_acesso=aluno_data.get("forma_acesso"),
                    dispensa_ensino_religioso=aluno_data.get("dispensa_ensino_religioso") is True,
                    serie_ano=aluno_data.get("serie_ano", ""),
                    turno_aluno=aluno_data.get("turno"),
                    turma_principal_id=aluno_data.get("turma_id") or None,
                    escola=escola,
                )

                # =========================
                # SAÚDE
                # =========================
                Saude.objects.create(
                    aluno=aluno,
                    possui_necessidade_especial=aluno_data.get("possui_necessidade_especial") is True,
                    descricao_necessidade=aluno_data.get("descricao_necessidade"),
                    possui_alergia=aluno_data.get("possui_alergia") is True,
                    descricao_alergia=aluno_data.get("descricao_alergia"),
                    usa_medicacao=aluno_data.get("usa_medicacao") is True,
                    quais_medicacoes=aluno_data.get("quais_medicacoes"),
                )

                # =========================
                # TRANSPORTE
                # =========================
                TransporteEscolar.objects.create(
                    aluno=aluno,
                    usa_transporte_escolar=aluno_data.get("usa_transporte_escolar") is True,
                    trajeto=aluno_data.get("trajeto"),
                )

                # =========================
                # AUTORIZAÇÕES
                # =========================
                Autorizacoes.objects.create(
                    aluno=aluno,
                    autorizacao_saida_sozinho=aluno_data.get("autorizacao_saida_sozinho") is True,
                    autorizacao_fotos_eventos=aluno_data.get("autorizacao_fotos_eventos") is True,
                    pessoa_autorizada_buscar=aluno_data.get("pessoa_autorizada_buscar"),
                    usa_transporte_publico=aluno_data.get("usa_transporte_publico") is True,
                )

                alunos_criados.append({
                    "aluno": index,
                    "id": aluno.id,
                    "nome": aluno.nome,
                    "matricula": aluno.matricula,
                })

        except (ValueError, IntegrityError) as e:
            erros.append({
                "aluno": index,
                "nome": aluno_data.get("nome"),
                "erro": str(e),
            })

        except Exception as e:
            erros.append({
                "aluno": index,
                "nome": aluno_data.get("nome"),
                "erro": "Erro inesperado ao salvar aluno",
                "detalhe": str(e),
            })

    # =========================
    # RESPOSTA FINAL
    # =========================
    if erros and alunos_criados:
        return JsonResponse(
            {
                "status": "parcial",
                "total_enviados": len(alunos_data),
                "salvos": len(alunos_criados),
                "erros": erros,
                "alunos": alunos_criados,
            }
        )

    if erros and not alunos_criados:
        return JsonResponse(
            {
                "status": "erro",
                "mensagem": "Nenhum aluno foi matriculado",
                "erros": erros,
            },
            status=400
        )

    return JsonResponse(
        {
            "status": "sucesso",
            "total": len(alunos_criados),
            "alunos": alunos_criados,
        }
    )


@login_required
def registro_matricula_lote(request):
    escola = getattr(request.user, "escola", None)

    turmas = []
    if escola:
        turmas = Turma.objects.filter(escola=escola).order_by("nome")

    return render(
        request,
        "pages/registro_lote.html",
        {"turmas": turmas}
    )

