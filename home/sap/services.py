from home.utils import registrar_auditoria


def salvar_nota(request, aluno, avaliacao, valor, conceito=None):

    from home.models import Nota

    nota_antiga = Nota.objects.filter(
        aluno=aluno,
        avaliacao=avaliacao,
        escola=request.escola
    ).first()

    antes = None
    if nota_antiga:
        antes = {
            "valor": str(nota_antiga.valor) if nota_antiga.valor is not None else None,
            "conceito": nota_antiga.conceito
        }

    nota, created = Nota.objects.update_or_create(
        aluno=aluno,
        avaliacao=avaliacao,
        escola=request.escola,
        defaults={
            "valor": valor,
            "conceito": conceito
        }
    )

    registrar_auditoria(
        request,
        acao="CREATE_NOTA" if created else "UPDATE_NOTA",
        obj=nota,
        antes=antes,
        depois={
            "valor": str(valor) if valor is not None else None,
            "conceito": conceito
        }
    )

    return nota


def criar_avaliacao(request, **data):

    from home.models import Avaliacao

    avaliacao = Avaliacao.objects.create(**data)

    registrar_auditoria(
        request,
        acao="CREATE_AVALIACAO",
        obj=avaliacao,
        depois={k: str(v) if v is not None else None for k, v in data.items()}
    )

    return avaliacao


def fechar_ano(request, ano):

    antes = {
        "ativo": ano.ativo,
        "encerrado": ano.encerrado
    }

    ano.ativo = False
    ano.encerrado = True
    ano.save()

    registrar_auditoria(
        request,
        acao="FECHAMENTO_ANO",
        obj=ano,
        antes=antes,
        depois={
            "ativo": False,
            "encerrado": True
        }
    )