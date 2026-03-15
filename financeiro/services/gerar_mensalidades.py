from financeiro.models import Mensalidade


def gerar_mensalidade(aluno, valor, vencimento, mes, ano):

    desconto = 0

    valor_final = valor - desconto

    Mensalidade.objects.create(
        escola=aluno.escola,
        aluno=aluno,
        responsavel_financeiro=aluno.responsavel_financeiro,
        mes_referencia=mes,
        ano_referencia=ano,
        valor_original=valor,
        desconto=desconto,
        valor_final=valor_final,
        vencimento=vencimento
    )