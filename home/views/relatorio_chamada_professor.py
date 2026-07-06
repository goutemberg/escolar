from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator

from home.models import Chamada, Docente, Turma


@login_required
def relatorio_chamada_professor(request):

    escola = request.user.escola

    chamadas = (
        Chamada.objects.select_related(
            "criado_por",
            "turma",
            "professor",
            "professor__user",
            "diario",  # mantido apenas por compatibilidade
        )
        .filter(escola=escola)
        .order_by("-criado_em")
    )

    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")
    professor_id = request.GET.get("professor")
    turma_id = request.GET.get("turma")

    busca = request.GET.get("busca")
    situacao = request.GET.get("situacao")

    page_size = request.GET.get("page_size", 25)

    try:
        page_size = int(page_size)
    except (ValueError, TypeError):
        page_size = 25

    # =====================================================
    # FILTROS
    # =====================================================

    if data_inicio:
        chamadas = chamadas.filter(data__gte=data_inicio)

    if data_fim:
        chamadas = chamadas.filter(data__lte=data_fim)

    if professor_id:
        chamadas = chamadas.filter(professor_id=professor_id)

    if turma_id:
        chamadas = chamadas.filter(turma_id=turma_id)

    if busca:
        chamadas = chamadas.filter(
            Q(professor__nome__icontains=busca)
            | Q(turma__nome__icontains=busca)
            | Q(criado_por__first_name__icontains=busca)
            | Q(criado_por__last_name__icontains=busca)
            | Q(criado_por__username__icontains=busca)
        )

    # =====================================================
    # SITUAÇÃO
    # =====================================================

    chamadas_lista = list(chamadas)

    if situacao in ["professor", "terceiro"]:

        chamadas_filtradas = []

        for chamada in chamadas_lista:

            professor_user_id = None

            if chamada.professor and chamada.professor.user:
                professor_user_id = chamada.professor.user.id

            foi_professor = professor_user_id == chamada.criado_por_id

            if situacao == "professor" and foi_professor:
                chamadas_filtradas.append(chamada)

            elif situacao == "terceiro" and not foi_professor:
                chamadas_filtradas.append(chamada)

        chamadas_lista = chamadas_filtradas

    # =====================================================
    # CARDS SUPERIORES
    # =====================================================

    total_chamadas = len(chamadas_lista)

    chamadas_professor = 0
    chamadas_terceiros = 0

    for chamada in chamadas_lista:

        professor_user_id = None

        if chamada.professor and chamada.professor.user:
            professor_user_id = chamada.professor.user.id

        if professor_user_id == chamada.criado_por_id:
            chamadas_professor += 1
        else:
            chamadas_terceiros += 1

    # =====================================================
    # PAGINAÇÃO
    # =====================================================

    paginator = Paginator(chamadas_lista, page_size)

    page_number = request.GET.get("page", 1)

    chamadas_paginadas = paginator.get_page(page_number)

    # =====================================================
    # FILTROS DA TELA
    # =====================================================

    professores = Docente.objects.filter(
        ativo=True,
        escola=escola,
    ).order_by("nome")

    turmas = Turma.objects.filter(escola=escola).order_by("nome")

    # =====================================================
    # MANTER FILTROS NA PAGINAÇÃO
    # =====================================================

    query_params = request.GET.copy()

    if "page" in query_params:
        query_params.pop("page")

    query_string = query_params.urlencode()

    contexto = {
        "chamadas": chamadas_paginadas,
        "professores": professores,
        "turmas": turmas,
        "total_chamadas": total_chamadas,
        "chamadas_professor": chamadas_professor,
        "chamadas_terceiros": chamadas_terceiros,
        "total_professores": professores.count(),
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "professor_selecionado": professor_id,
        "turma_selecionada": turma_id,
        "busca": busca,
        "situacao_selecionada": situacao,
        "page_size": page_size,
        "query_string": query_string,
    }

    return render(
        request,
        "pages/chamada/relatorio_chamada_professor.html",
        contexto,
    )
