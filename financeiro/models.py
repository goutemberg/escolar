from django.db import models
from home.models import Aluno, Escola
from datetime import date
from decimal import Decimal




class Mensalidade(models.Model):

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("pago", "Pago"),
    ]

    MESES = [
        "",
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name="mensalidades"
    )

    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name="mensalidades"
    )

    mes_referencia = models.IntegerField()
    ano_referencia = models.IntegerField()

    valor_original = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    desconto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valor_final = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    vencimento = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pendente"
    )

    gateway_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    pago_em = models.DateTimeField(
        null=True,
        blank=True
    )

    responsavel_snapshot = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    # -----------------------------------
    # Métodos auxiliares
    # -----------------------------------

    def mes_nome(self):
        return self.MESES[self.mes_referencia]

    def status_atual(self):

        if self.status == "pago":
            return "pago"

        if self.vencimento < date.today():
            return "vencido"

        return "pendente"

    def valor_atualizado(self):

        valor = self.valor_final

        # se já foi pago não altera
        if self.status == "pago":
            return valor

        hoje = date.today()

        # se ainda não venceu
        if hoje <= self.vencimento:
            return valor

        dias_atraso = (hoje - self.vencimento).days

        # multa fixa 2%
        multa = valor * Decimal("0.02")

        # juros diário (~1% ao mês)
        juros = valor * Decimal("0.00033") * dias_atraso

        return (valor + multa + juros).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.aluno.nome} - {self.mes_nome()}/{self.ano_referencia}"

    # -----------------------------------
    # Meta
    # -----------------------------------

    class Meta:

        unique_together = ("aluno", "mes_referencia", "ano_referencia")

        indexes = [
            models.Index(fields=["escola"]),
            models.Index(fields=["status"]),
            models.Index(fields=["vencimento"]),
        ]

        ordering = ["vencimento"]
    

class Pagamento(models.Model):

    mensalidade = models.ForeignKey(
        Mensalidade,
        on_delete=models.CASCADE,
        related_name="pagamentos"
    )

    valor = models.DecimalField(max_digits=10, decimal_places=2)

    metodo = models.CharField(
        max_length=30,
        choices=[
            ('pix', 'PIX'),
            ('boleto', 'Boleto'),
            ('cartao', 'Cartão'),
            ('manual', 'Manual')
        ]
    )

    data_pagamento = models.DateTimeField()

    referencia_gateway = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )