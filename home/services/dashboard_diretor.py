from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count, Q

from home.models import (
    Avaliacao,
    Chamada,
    Matricula,
    Nota,
    Presenca,
    TurmaDisciplina,
)
from home.utils import get_ano_ativo, get_turmas_ativas

LIMITE_FREQUENCIA_ATENCAO = Decimal("75.00")
LIMITE_MEDIA_ATENCAO = Decimal("6.00")
LIMITE_PONTOS_ATENCAO = 5


# ============================================================
# UTILITÁRIOS
# ============================================================


def _percentual(valor, total):
    if not total:
        return None

    resultado = (Decimal(valor) / Decimal(total)) * Decimal("100")

    return resultado.quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )


def _decimal_uma_casa(valor):
    if valor is None:
        return None

    return Decimal(valor).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )


# ============================================================
# FREQUÊNCIA
# ============================================================


def _obter_frequencia_escola(escola, ano_letivo):
    resultado = Presenca.objects.filter(
        chamada__escola=escola,
        chamada__turma__ano_letivo=ano_letivo,
        aluno__matriculas__ano_letivo=ano_letivo,
        aluno__matriculas__status="ATIVA",
    ).aggregate(
        total=Count("id"),
        presentes=Count(
            "id",
            filter=Q(status="P"),
        ),
    )

    return _percentual(
        resultado["presentes"],
        resultado["total"],
    )


def _obter_media_escola(escola, ano_letivo):
    resultado = Nota.objects.filter(
        escola=escola,
        avaliacao__escola=escola,
        avaliacao__turma__ano_letivo=ano_letivo,
        aluno__matriculas__ano_letivo=ano_letivo,
        aluno__matriculas__status="ATIVA",
        valor__isnull=False,
    ).aggregate(
        media=Avg("valor"),
    )

    return _decimal_uma_casa(resultado["media"])


def _obter_frequencia_por_turma(turma, ano_letivo):
    resultado = Presenca.objects.filter(
        chamada__turma=turma,
        chamada__turma__ano_letivo=ano_letivo,
        aluno__matriculas__ano_letivo=ano_letivo,
        aluno__matriculas__status="ATIVA",
    ).aggregate(
        total=Count("id"),
        presentes=Count(
            "id",
            filter=Q(status="P"),
        ),
    )

    return _percentual(
        resultado["presentes"],
        resultado["total"],
    )


def _obter_media_por_turma(turma, ano_letivo):
    resultado = Nota.objects.filter(
        escola=turma.escola,
        avaliacao__turma=turma,
        avaliacao__turma__ano_letivo=ano_letivo,
        aluno__matriculas__ano_letivo=ano_letivo,
        aluno__matriculas__status="ATIVA",
        valor__isnull=False,
    ).aggregate(
        media=Avg("valor"),
    )

    return _decimal_uma_casa(resultado["media"])


# ============================================================
# DADOS CONSOLIDADOS DAS TURMAS
# ============================================================


def _obter_dados_turmas(escola, ano_letivo):
    """
    Carrega todos os indicadores necessários das turmas em
    consultas agrupadas.

    O objetivo é evitar N+1 queries no dashboard principal.
    """

    turmas = list(
        get_turmas_ativas(escola)
        .filter(status="ATIVA")
        .select_related("ano_letivo")
        .order_by(
            "ano",
            "nome",
            "turno",
        )
    )

    if not turmas:
        return {
            "turmas": [],
            "por_id": {},
            "total_alunos": 0,
            "alunos_sem_turma": 0,
        }

    turma_ids = [turma.id for turma in turmas]

    # --------------------------------------------------------
    # MATRÍCULAS POR TURMA
    # --------------------------------------------------------

    matriculas_por_turma = {
        item["turma_id"]: item["total"]
        for item in (
            Matricula.objects.filter(
                aluno__escola=escola,
                ano_letivo=ano_letivo,
                status="ATIVA",
            )
            .values("turma_id")
            .annotate(total=Count("id"))
        )
    }

    total_alunos = sum(matriculas_por_turma.values())

    alunos_sem_turma = matriculas_por_turma.get(
        None,
        0,
    )

    # --------------------------------------------------------
    # FREQUÊNCIA POR TURMA
    # --------------------------------------------------------

    frequencia_por_turma = {}

    presencas_por_turma = (
        Presenca.objects.filter(
            chamada__escola=escola,
            chamada__turma__ano_letivo=ano_letivo,
            chamada__turma__status="ATIVA",
            aluno__matriculas__ano_letivo=ano_letivo,
            aluno__matriculas__status="ATIVA",
        )
        .values("chamada__turma_id")
        .annotate(
            total=Count("id"),
            presentes=Count(
                "id",
                filter=Q(status="P"),
            ),
        )
    )

    for item in presencas_por_turma:
        frequencia_por_turma[item["chamada__turma_id"]] = _percentual(
            item["presentes"],
            item["total"],
        )

    # --------------------------------------------------------
    # MÉDIA POR TURMA
    # --------------------------------------------------------

    media_por_turma = {}

    medias = (
        Nota.objects.filter(
            escola=escola,
            avaliacao__escola=escola,
            avaliacao__turma__ano_letivo=ano_letivo,
            avaliacao__turma__status="ATIVA",
            aluno__matriculas__ano_letivo=ano_letivo,
            aluno__matriculas__status="ATIVA",
            valor__isnull=False,
        )
        .values("avaliacao__turma_id")
        .annotate(
            media=Avg("valor"),
        )
    )

    for item in medias:
        media_por_turma[item["avaliacao__turma_id"]] = _decimal_uma_casa(item["media"])

    # --------------------------------------------------------
    # CHAMADAS POR TURMA
    # --------------------------------------------------------

    chamadas_por_turma = {
        item["turma_id"]: item["total"]
        for item in (
            Chamada.objects.filter(
                escola=escola,
                turma__ano_letivo=ano_letivo,
                turma__status="ATIVA",
            )
            .values("turma_id")
            .annotate(total=Count("id"))
        )
    }

    # --------------------------------------------------------
    # MONTAGEM FINAL
    # --------------------------------------------------------

    dados = []
    por_id = {}

    for turma in turmas:
        item = {
            "id": turma.id,
            "nome": turma.nome,
            "ano": turma.ano,
            "turno": turma.turno,
            "sala": turma.sala,
            "total_alunos": matriculas_por_turma.get(
                turma.id,
                0,
            ),
            "frequencia": frequencia_por_turma.get(turma.id),
            "media": media_por_turma.get(turma.id),
            "total_chamadas": chamadas_por_turma.get(
                turma.id,
                0,
            ),
            "turma": turma,
        }

        dados.append(item)
        por_id[turma.id] = item

    return {
        "turmas": dados,
        "por_id": por_id,
        "total_alunos": total_alunos,
        "alunos_sem_turma": alunos_sem_turma,
    }


# ============================================================
# TURMAS EM ATENÇÃO
# ============================================================


def _obter_turmas_atencao(
    escola,
    ano_letivo,
    dados_turmas=None,
):
    if dados_turmas is None:
        dados_turmas = _obter_dados_turmas(
            escola,
            ano_letivo,
        )

    resultado = []

    for item in dados_turmas["turmas"]:
        frequencia = item["frequencia"]
        media = item["media"]

        motivos = []

        if frequencia is not None and frequencia < LIMITE_FREQUENCIA_ATENCAO:
            motivos.append(f"frequência {frequencia}%")

        if media is not None and media < LIMITE_MEDIA_ATENCAO:
            motivos.append(f"média {media}")

        if motivos:
            resultado.append(
                {
                    "id": item["id"],
                    "nome": item["nome"],
                    "turno": item["turno"],
                    "frequencia": frequencia,
                    "media": media,
                    "motivos": motivos,
                }
            )

    return resultado


# ============================================================
# VISÃO DAS TURMAS
# ============================================================


def _obter_turmas_dashboard(
    escola,
    ano_letivo,
    dados_turmas=None,
):
    if dados_turmas is None:
        dados_turmas = _obter_dados_turmas(
            escola,
            ano_letivo,
        )

    resultado = []

    for item in dados_turmas["turmas"]:
        resultado.append(
            {
                "id": item["id"],
                "nome": item["nome"],
                "ano": item["ano"],
                "turno": item["turno"],
                "sala": item["sala"],
                "total_alunos": item["total_alunos"],
                "frequencia": item["frequencia"],
                "media": item["media"],
            }
        )

    return resultado


# ============================================================
# SAÚDE OPERACIONAL
# ============================================================


def _obter_saude_operacional(
    escola,
    ano_letivo,
    dados_turmas=None,
):
    """
    Calcula os indicadores operacionais da escola.

    Esta versão utiliza os dados consolidados das turmas para
    evitar consultas dentro de loops.
    """

    if dados_turmas is None:
        dados_turmas = _obter_dados_turmas(
            escola,
            ano_letivo,
        )

    turmas = dados_turmas["turmas"]

    total_turmas = len(turmas)

    # ========================================================
    # MATRÍCULAS
    # ========================================================

    total_alunos = dados_turmas["total_alunos"]
    alunos_sem_turma = dados_turmas["alunos_sem_turma"]

    if alunos_sem_turma > 0:
        matriculas_status = "atencao"

        matriculas_descricao = (
            f"{alunos_sem_turma} "
            f"{'aluno está' if alunos_sem_turma == 1 else 'alunos estão'} "
            f"sem turma definida."
        )

    elif total_alunos > 0:
        matriculas_status = "operacional"

        matriculas_descricao = (
            f"{total_alunos} "
            f"{'aluno matriculado' if total_alunos == 1 else 'alunos matriculados'} "
            f"no ano letivo atual."
        )

    else:
        matriculas_status = "sem_dados"

        matriculas_descricao = (
            "Ainda não existem alunos com matrícula ativa " "no ano letivo atual."
        )

    matriculas = {
        "chave": "matriculas",
        "titulo": "Matrículas",
        "status": matriculas_status,
        "descricao": matriculas_descricao,
        "quantidade": alunos_sem_turma,
    }

    # ========================================================
    # TURMAS
    # ========================================================

    turmas_sem_alunos = [item for item in turmas if item["total_alunos"] == 0]

    total_turmas_sem_alunos = len(turmas_sem_alunos)

    if total_turmas_sem_alunos > 0:
        turmas_status = "atencao"

        turmas_descricao = (
            f"{total_turmas_sem_alunos} "
            f"{'turma está' if total_turmas_sem_alunos == 1 else 'turmas estão'} "
            f"sem alunos matriculados."
        )

    elif total_turmas > 0:
        turmas_status = "operacional"

        turmas_descricao = (
            f"{total_turmas} "
            f"{'turma ativa' if total_turmas == 1 else 'turmas ativas'} "
            f"com alunos vinculados."
        )

    else:
        turmas_status = "sem_dados"

        turmas_descricao = "Não existem turmas ativas no ano letivo atual."

    turmas_indicador = {
        "chave": "turmas",
        "titulo": "Turmas",
        "status": turmas_status,
        "descricao": turmas_descricao,
        "quantidade": total_turmas_sem_alunos,
    }

    # ========================================================
    # PROFESSORES
    # ========================================================

    professores_resumo = TurmaDisciplina.objects.filter(
        escola=escola,
        turma__ano_letivo=ano_letivo,
        turma__status="ATIVA",
    ).aggregate(
        total=Count("id"),
        sem_professor=Count(
            "id",
            filter=Q(professor__isnull=True),
        ),
    )

    disciplinas_sem_professor = professores_resumo["sem_professor"] or 0

    total_vinculos = professores_resumo["total"] or 0

    if disciplinas_sem_professor > 0:
        professores_status = "atencao"

        professores_descricao = (
            f"{disciplinas_sem_professor} "
            f"{'disciplina está' if disciplinas_sem_professor == 1 else 'disciplinas estão'} "
            f"sem professor vinculado."
        )

    elif total_vinculos > 0:
        professores_status = "operacional"

        professores_descricao = (
            f"{total_vinculos} "
            f"{'vínculo pedagógico registrado' if total_vinculos == 1 else 'vínculos pedagógicos registrados'}."
        )

    else:
        professores_status = "sem_dados"

        professores_descricao = "Ainda não existem disciplinas vinculadas às turmas."

    professores = {
        "chave": "professores",
        "titulo": "Professores",
        "status": professores_status,
        "descricao": professores_descricao,
        "quantidade": disciplinas_sem_professor,
    }

    # ========================================================
    # FREQUÊNCIA
    # ========================================================

    frequencia = _obter_frequencia_escola(
        escola,
        ano_letivo,
    )

    if frequencia is None:
        frequencia_status = "sem_dados"

        frequencia_descricao = (
            "Ainda não existem registros de frequência " "suficientes para análise."
        )

    elif frequencia < LIMITE_FREQUENCIA_ATENCAO:
        frequencia_status = "atencao"

        frequencia_descricao = (
            f"Frequência geral de {frequencia}%, "
            f"abaixo do indicador de atenção de "
            f"{LIMITE_FREQUENCIA_ATENCAO}%."
        )

    else:
        frequencia_status = "boa"

        frequencia_descricao = f"Frequência geral de {frequencia}%."

    frequencia_indicador = {
        "chave": "frequencia",
        "titulo": "Frequência",
        "status": frequencia_status,
        "descricao": frequencia_descricao,
        "valor": frequencia,
    }

    # ========================================================
    # REGISTROS PEDAGÓGICOS
    # ========================================================

    total_turmas_sem_chamada = sum(1 for item in turmas if item["total_chamadas"] == 0)

    if total_turmas == 0:
        registros_status = "sem_dados"

        registros_descricao = "Não existem turmas ativas para análise."

    elif total_turmas_sem_chamada > 0:
        registros_status = "atencao"

        registros_descricao = (
            f"{total_turmas_sem_chamada} "
            f"{'turma ainda não possui' if total_turmas_sem_chamada == 1 else 'turmas ainda não possuem'} "
            f"registro de chamada."
        )

    else:
        registros_status = "operacional"

        registros_descricao = "Todas as turmas possuem registros de chamada."

    registros_pedagogicos = {
        "chave": "registros_pedagogicos",
        "titulo": "Registros pedagógicos",
        "status": registros_status,
        "descricao": registros_descricao,
        "quantidade": total_turmas_sem_chamada,
    }

    # ========================================================
    # AVALIAÇÕES
    # ========================================================

    avaliacoes = Avaliacao.objects.filter(
        escola=escola,
        turma__ano_letivo=ano_letivo,
        turma__status="ATIVA",
    )

    total_avaliacoes = avaliacoes.count()

    avaliacoes_com_nota = (
        avaliacoes.filter(nota__valor__isnull=False).values("id").distinct()
    )

    total_avaliacoes_com_nota = avaliacoes_com_nota.count()

    avaliacoes_sem_notas = total_avaliacoes - total_avaliacoes_com_nota

    if total_avaliacoes == 0:
        avaliacoes_status = "sem_dados"

        avaliacoes_descricao = (
            "Ainda não existem avaliações cadastradas " "para as turmas ativas."
        )

    elif avaliacoes_sem_notas > 0:
        avaliacoes_status = "atencao"

        avaliacoes_descricao = (
            f"{avaliacoes_sem_notas} "
            f"{'avaliação ainda não possui' if avaliacoes_sem_notas == 1 else 'avaliações ainda não possuem'} "
            f"notas lançadas."
        )

    else:
        avaliacoes_status = "boa"

        avaliacoes_descricao = (
            f"{total_avaliacoes} "
            f"{'avaliação registrada' if total_avaliacoes == 1 else 'avaliações registradas'} "
            f"com notas lançadas."
        )

    avaliacoes_indicador = {
        "chave": "avaliacoes",
        "titulo": "Avaliações",
        "status": avaliacoes_status,
        "descricao": avaliacoes_descricao,
        "quantidade": avaliacoes_sem_notas,
    }

    # ========================================================
    # FINANCEIRO
    # ========================================================

    financeiro = {
        "chave": "financeiro",
        "titulo": "Financeiro",
        "status": "analise",
        "descricao": (
            "Os indicadores financeiros serão integrados "
            "à visão executiva do diretor."
        ),
        "quantidade": None,
    }

    # ========================================================
    # RESUMO
    # ========================================================

    indicadores = [
        matriculas,
        turmas_indicador,
        professores,
        frequencia_indicador,
        registros_pedagogicos,
        avaliacoes_indicador,
        financeiro,
    ]

    total_atencao = sum(
        1 for indicador in indicadores if indicador["status"] == "atencao"
    )

    if total_atencao == 0:
        resumo = {
            "status": "operacional",
            "quantidade": 0,
            "mensagem": ("Nenhum ponto operacional requer atenção."),
        }

    elif total_atencao == 1:
        resumo = {
            "status": "atencao",
            "quantidade": 1,
            "mensagem": ("1 ponto requer a atenção do diretor."),
        }

    else:
        resumo = {
            "status": "atencao",
            "quantidade": total_atencao,
            "mensagem": (f"{total_atencao} pontos requerem " "a atenção do diretor."),
        }

    return {
        "indicadores": indicadores,
        "resumo": resumo,
        "total_atencao": total_atencao,
    }


# ============================================================
# PONTOS DE ATENÇÃO
# ============================================================


def _obter_pontos_atencao(
    saude_operacional,
    turmas_atencao,
):
    pontos = []

    indicadores = {
        indicador["chave"]: indicador
        for indicador in saude_operacional.get(
            "indicadores",
            [],
        )
    }

    # ========================================================
    # 1. MATRÍCULAS SEM TURMA
    # ========================================================

    matriculas = indicadores.get("matriculas")

    if (
        matriculas
        and matriculas.get("status") == "atencao"
        and matriculas.get("quantidade", 0) > 0
    ):
        quantidade = matriculas["quantidade"]

        pontos.append(
            {
                "nivel": "alta",
                "tipo": "matriculas",
                "titulo": (
                    f"{quantidade} "
                    f"{'aluno está' if quantidade == 1 else 'alunos estão'} "
                    "sem turma definida"
                ),
                "descricao": (
                    "Existem matrículas ativas no ano letivo atual "
                    "que ainda não possuem turma vinculada."
                ),
                "quantidade": quantidade,
            }
        )

    # ========================================================
    # 2. DISCIPLINAS SEM PROFESSOR
    # ========================================================

    professores = indicadores.get("professores")

    if (
        professores
        and professores.get("status") == "atencao"
        and professores.get("quantidade", 0) > 0
    ):
        quantidade = professores["quantidade"]

        pontos.append(
            {
                "nivel": "alta",
                "tipo": "professores",
                "titulo": (
                    f"{quantidade} "
                    f"{'disciplina está' if quantidade == 1 else 'disciplinas estão'} "
                    "sem professor vinculado"
                ),
                "descricao": (
                    "Existem vínculos pedagógicos de turmas ativas "
                    "que ainda não possuem professor definido."
                ),
                "quantidade": quantidade,
            }
        )

    # ========================================================
    # 3. TURMAS SEM REGISTRO DE CHAMADA
    # ========================================================

    registros = indicadores.get("registros_pedagogicos")

    if (
        registros
        and registros.get("status") == "atencao"
        and registros.get("quantidade", 0) > 0
    ):
        quantidade = registros["quantidade"]

        pontos.append(
            {
                "nivel": "media",
                "tipo": "registros_pedagogicos",
                "titulo": (
                    f"{quantidade} "
                    f"{'turma ainda não possui' if quantidade == 1 else 'turmas ainda não possuem'} "
                    "registro de chamada"
                ),
                "descricao": (
                    "Verifique as turmas que ainda não possuem "
                    "registros de frequência no ano letivo atual."
                ),
                "quantidade": quantidade,
            }
        )

    # ========================================================
    # 4. AVALIAÇÕES SEM NOTAS
    # ========================================================

    avaliacoes = indicadores.get("avaliacoes")

    if (
        avaliacoes
        and avaliacoes.get("status") == "atencao"
        and avaliacoes.get("quantidade", 0) > 0
    ):
        quantidade = avaliacoes["quantidade"]

        pontos.append(
            {
                "nivel": "media",
                "tipo": "avaliacoes",
                "titulo": (
                    f"{quantidade} "
                    f"{'avaliação ainda não possui' if quantidade == 1 else 'avaliações ainda não possuem'} "
                    "notas lançadas"
                ),
                "descricao": (
                    "Existem avaliações cadastradas para turmas "
                    "ativas sem notas lançadas."
                ),
                "quantidade": quantidade,
            }
        )

    # ========================================================
    # 5. FREQUÊNCIA GERAL
    # ========================================================

    frequencia = indicadores.get("frequencia")

    if frequencia and frequencia.get("status") == "atencao":
        valor = frequencia.get("valor")

        pontos.append(
            {
                "nivel": "alta",
                "tipo": "frequencia",
                "titulo": (f"Frequência geral de {valor}%"),
                "descricao": (
                    f"A frequência geral está abaixo do "
                    f"indicador de atenção de "
                    f"{LIMITE_FREQUENCIA_ATENCAO}%."
                ),
                "quantidade": None,
            }
        )

    # ========================================================
    # 6. TURMAS COM INDICADORES ABAIXO DO ESPERADO
    # ========================================================

    if turmas_atencao:
        possui_ponto_operacional = any(ponto["tipo"] != "turmas" for ponto in pontos)

        if not possui_ponto_operacional:
            quantidade = len(turmas_atencao)

            pontos.append(
                {
                    "nivel": "media",
                    "tipo": "turmas",
                    "titulo": (
                        f"{quantidade} "
                        f"{'turma apresenta' if quantidade == 1 else 'turmas apresentam'} "
                        "indicadores de atenção"
                    ),
                    "descricao": (
                        "Há turmas com frequência ou desempenho "
                        "abaixo dos indicadores definidos."
                    ),
                    "quantidade": quantidade,
                }
            )

    # ========================================================
    # ORDEM DE PRIORIDADE
    # ========================================================

    prioridade = {
        "alta": 1,
        "media": 2,
        "baixa": 3,
    }

    pontos.sort(
        key=lambda ponto: prioridade.get(
            ponto.get("nivel"),
            99,
        )
    )

    return pontos[:LIMITE_PONTOS_ATENCAO]


# ============================================================
# DASHBOARD PRINCIPAL
# ============================================================


def obter_dashboard_diretor(user):
    escola = getattr(
        user,
        "escola",
        None,
    )

    ano_letivo = get_ano_ativo()

    contexto = {
        "escola": escola,
        "ano_letivo": ano_letivo,
        "metricas": {
            "alunos_ativos": 0,
            "turmas_ativas": 0,
            "frequencia": None,
            "media_escola": None,
        },
        "turmas_atencao": [],
        "turmas": [],
        "alertas": [],
        "saude_operacional": {
            "indicadores": [],
            "resumo": {
                "status": "sem_dados",
                "quantidade": 0,
                "mensagem": ("Não foi possível calcular " "a saúde operacional."),
            },
            "total_atencao": 0,
        },
        "pontos_atencao": [],
    }

    # ========================================================
    # ESCOLA
    # ========================================================

    if not escola:
        contexto["alertas"].append(
            {
                "tipo": "danger",
                "titulo": "Escola não identificada",
                "descricao": ("O usuário não possui uma escola vinculada."),
            }
        )

        contexto["pontos_atencao"] = [
            {
                "nivel": "alta",
                "tipo": "escola",
                "titulo": "Escola não identificada",
                "descricao": ("O usuário não possui uma escola vinculada."),
                "quantidade": None,
            }
        ]

        return contexto

    # ========================================================
    # ANO LETIVO
    # ========================================================

    if not ano_letivo:
        contexto["alertas"].append(
            {
                "tipo": "warning",
                "titulo": "Ano letivo não configurado",
                "descricao": ("Não existe um ano letivo ativo no momento."),
            }
        )

        contexto["pontos_atencao"] = [
            {
                "nivel": "alta",
                "tipo": "ano_letivo",
                "titulo": "Ano letivo não configurado",
                "descricao": ("Não existe um ano letivo ativo no momento."),
                "quantidade": None,
            }
        ]

        return contexto

    # ========================================================
    # DADOS CONSOLIDADOS DAS TURMAS
    # ========================================================
    #
    # IMPORTANTE:
    # Esta consulta consolidada é criada uma única vez e
    # reutilizada pelo dashboard, pelas turmas em atenção e
    # pela saúde operacional.
    #
    # ========================================================

    dados_turmas = _obter_dados_turmas(
        escola,
        ano_letivo,
    )

    # ========================================================
    # MÉTRICAS EXECUTIVAS
    # ========================================================

    contexto["metricas"]["alunos_ativos"] = dados_turmas["total_alunos"]

    contexto["metricas"]["turmas_ativas"] = len(dados_turmas["turmas"])

    contexto["metricas"]["frequencia"] = _obter_frequencia_escola(
        escola,
        ano_letivo,
    )

    contexto["metricas"]["media_escola"] = _obter_media_escola(
        escola,
        ano_letivo,
    )

    # ========================================================
    # VISÃO DAS TURMAS
    # ========================================================

    contexto["turmas"] = _obter_turmas_dashboard(
        escola,
        ano_letivo,
        dados_turmas=dados_turmas,
    )

    # ========================================================
    # TURMAS EM ATENÇÃO
    # ========================================================

    contexto["turmas_atencao"] = _obter_turmas_atencao(
        escola,
        ano_letivo,
        dados_turmas=dados_turmas,
    )

    # ========================================================
    # SAÚDE OPERACIONAL
    # ========================================================

    contexto["saude_operacional"] = _obter_saude_operacional(
        escola,
        ano_letivo,
        dados_turmas=dados_turmas,
    )

    # ========================================================
    # PONTOS DE ATENÇÃO
    # ========================================================

    contexto["pontos_atencao"] = _obter_pontos_atencao(
        contexto["saude_operacional"],
        contexto["turmas_atencao"],
    )

    return contexto


# ============================================================
# DIAGNÓSTICO DA TURMA
# ============================================================


def obter_detalhamento_turma(turma, ano_letivo):
    matriculas = (
        Matricula.objects.filter(
            turma=turma,
            ano_letivo=ano_letivo,
            status="ATIVA",
        )
        .select_related("aluno")
        .order_by("aluno__nome")
    )

    alunos = []

    total_presencas_turma = 0
    total_presentes_turma = 0

    soma_notas_turma = Decimal("0")
    quantidade_notas_turma = 0

    for matricula in matriculas:
        aluno = matricula.aluno

        presencas = Presenca.objects.filter(
            chamada__turma=turma,
            chamada__turma__ano_letivo=ano_letivo,
            aluno=aluno,
        )

        total_presencas = presencas.count()

        presentes = presencas.filter(status="P").count()

        frequencia = _percentual(
            presentes,
            total_presencas,
        )

        resultado_nota = Nota.objects.filter(
            escola=turma.escola,
            avaliacao__turma=turma,
            avaliacao__turma__ano_letivo=ano_letivo,
            aluno=aluno,
            valor__isnull=False,
        ).aggregate(media=Avg("valor"))

        media = _decimal_uma_casa(resultado_nota["media"])

        total_presencas_turma += total_presencas
        total_presentes_turma += presentes

        if media is not None:
            soma_notas_turma += media
            quantidade_notas_turma += 1

        motivos = []

        if frequencia is not None and frequencia < LIMITE_FREQUENCIA_ATENCAO:
            motivos.append(f"frequência {frequencia}%")

        if media is not None and media < LIMITE_MEDIA_ATENCAO:
            motivos.append(f"média {media}")

        alunos.append(
            {
                "id": aluno.id,
                "nome": aluno.nome,
                "frequencia": frequencia,
                "media": media,
                "motivos": motivos,
                "precisa_atencao": bool(motivos),
            }
        )

    frequencia_turma = _percentual(
        total_presentes_turma,
        total_presencas_turma,
    )

    media_turma = None

    if quantidade_notas_turma:
        media_turma = _decimal_uma_casa(soma_notas_turma / quantidade_notas_turma)

    alunos_atencao = [aluno for aluno in alunos if aluno["precisa_atencao"]]

    alunos_atencao.sort(
        key=lambda aluno: (
            aluno["frequencia"] if aluno["frequencia"] is not None else Decimal("999"),
            aluno["nome"],
        )
    )

    return {
        "turma": turma,
        "total_alunos": len(alunos),
        "frequencia": frequencia_turma,
        "media": media_turma,
        "alunos": alunos,
        "alunos_atencao": alunos_atencao,
    }


# ============================================================
# DIAGNÓSTICO DO ALUNO
# ============================================================


def obter_detalhamento_aluno(aluno, ano_letivo):
    matricula = (
        Matricula.objects.filter(
            aluno=aluno,
            ano_letivo=ano_letivo,
            status="ATIVA",
        )
        .select_related(
            "aluno",
            "turma",
            "turma__ano_letivo",
        )
        .first()
    )

    if not matricula:
        return None

    turma = matricula.turma

    presencas = Presenca.objects.filter(
        chamada__turma=turma,
        chamada__turma__ano_letivo=ano_letivo,
        aluno=aluno,
    )

    resultado_presencas = presencas.aggregate(
        total=Count("id"),
        presentes=Count(
            "id",
            filter=Q(status="P"),
        ),
        justificadas=Count(
            "id",
            filter=Q(status="J"),
        ),
        faltas=Count(
            "id",
            filter=Q(status="F"),
        ),
    )

    total_presencas = resultado_presencas["total"] or 0

    presentes = resultado_presencas["presentes"] or 0

    justificadas = resultado_presencas["justificadas"] or 0

    faltas = resultado_presencas["faltas"] or 0

    frequencia = _percentual(
        presentes,
        total_presencas,
    )

    notas = Nota.objects.filter(
        escola=turma.escola,
        avaliacao__turma=turma,
        avaliacao__turma__ano_letivo=ano_letivo,
        aluno=aluno,
        valor__isnull=False,
    )

    resultado_media = notas.aggregate(media=Avg("valor"))

    media = _decimal_uma_casa(resultado_media["media"])

    avaliacoes = []

    notas = notas.select_related(
        "avaliacao",
        "avaliacao__disciplina",
    ).order_by(
        "avaliacao__disciplina__nome",
        "avaliacao__bimestre",
    )

    for nota in notas:
        disciplina = getattr(
            nota.avaliacao,
            "disciplina",
            None,
        )

        disciplina_nome = disciplina.nome if disciplina else "Disciplina não informada"

        avaliacoes.append(
            {
                "id": nota.id,
                "disciplina": disciplina_nome,
                "bimestre": nota.avaliacao.bimestre,
                "valor": _decimal_uma_casa(nota.valor),
                "conceito": getattr(
                    nota,
                    "conceito",
                    None,
                ),
                "recuperacao": getattr(
                    nota,
                    "recuperacao",
                    None,
                ),
            }
        )

    motivos_atencao = []

    if frequencia is not None and frequencia < LIMITE_FREQUENCIA_ATENCAO:
        motivos_atencao.append(f"frequência {frequencia}%")

    if media is not None and media < LIMITE_MEDIA_ATENCAO:
        motivos_atencao.append(f"média {media}")

    return {
        "aluno": aluno,
        "matricula": matricula,
        "turma": turma,
        "frequencia": frequencia,
        "total_presencas": total_presencas,
        "presentes": presentes,
        "faltas": faltas,
        "justificadas": justificadas,
        "media": media,
        "avaliacoes": avaliacoes,
        "motivos_atencao": motivos_atencao,
        "precisa_atencao": bool(motivos_atencao),
    }
