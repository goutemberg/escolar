from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from home.models import (
    Chamada,
    Docente,
    Turma
)


@login_required
def relatorio_chamada_professor(request):

    escola = request.user.escola

    chamadas = (
        Chamada.objects
        .select_related(
            'criado_por',
            'diario',
            'diario__turma',
            'diario__professor',
            'diario__professor__user'
        )
        .filter(
            diario__escola=escola
        )
        .order_by('-criado_em')
    )

    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    professor_id = request.GET.get('professor')
    turma_id = request.GET.get('turma')

    # NOVOS FILTROS
    busca = request.GET.get('busca')
    situacao = request.GET.get('situacao')

    if data_inicio:
        chamadas = chamadas.filter(
            diario__data_ministrada__gte=data_inicio
        )

    if data_fim:
        chamadas = chamadas.filter(
            diario__data_ministrada__lte=data_fim
        )

    if professor_id:
        chamadas = chamadas.filter(
            diario__professor_id=professor_id
        )

    if turma_id:
        chamadas = chamadas.filter(
            diario__turma_id=turma_id
        )

    # BUSCA LIVRE
    if busca:

        chamadas = chamadas.filter(

            Q(diario__professor__nome__icontains=busca)

            |

            Q(diario__turma__nome__icontains=busca)

            |

            Q(criado_por__first_name__icontains=busca)

            |

            Q(criado_por__last_name__icontains=busca)

            |

            Q(criado_por__username__icontains=busca)

        )

    # FILTRO SITUAÇÃO
    if situacao in ['professor', 'terceiro']:

        chamadas_filtradas = []

        for chamada in chamadas:

            professor_user_id = None

            if (
                chamada.diario
                and chamada.diario.professor
                and chamada.diario.professor.user
            ):
                professor_user_id = chamada.diario.professor.user.id

            foi_professor = (
                professor_user_id ==
                chamada.criado_por_id
            )

            if situacao == 'professor' and foi_professor:
                chamadas_filtradas.append(chamada)

            elif situacao == 'terceiro' and not foi_professor:
                chamadas_filtradas.append(chamada)

        chamadas = chamadas_filtradas

    professores = (
        Docente.objects
        .filter(
            ativo=True,
            escola=escola
        )
        .order_by('nome')
    )

    turmas = (
        Turma.objects
        .filter(
            escola=escola
        )
        .order_by('nome')
    )

    total_chamadas = len(chamadas)

    chamadas_professor = 0
    chamadas_terceiros = 0

    for chamada in chamadas:

        professor_user_id = None

        if (
            chamada.diario
            and chamada.diario.professor
            and chamada.diario.professor.user
        ):
            professor_user_id = chamada.diario.professor.user.id

        if professor_user_id == chamada.criado_por_id:
            chamadas_professor += 1
        else:
            chamadas_terceiros += 1

    contexto = {

        'chamadas': chamadas,

        'professores': professores,
        'turmas': turmas,

        'total_chamadas': total_chamadas,
        'chamadas_professor': chamadas_professor,
        'chamadas_terceiros': chamadas_terceiros,
        'total_professores': professores.count(),

        'data_inicio': data_inicio,
        'data_fim': data_fim,

        'professor_selecionado': professor_id,
        'turma_selecionada': turma_id,

        # NOVOS
        'busca': busca,
        'situacao_selecionada': situacao,
    }

    return render(
        request,
        'pages/chamada/relatorio_chamada_professor.html',
        contexto
    )