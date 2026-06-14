from django.core.management.base import BaseCommand

from home.models import (
    AnoLetivo,
    Turma,
    Avaliacao,
)


class Command(BaseCommand):

    help = "Vincula registros sem ano letivo ao ano informado"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ano",
            type=int,
            required=True
        )

    def handle(self, *args, **options):

        ano_numero = options["ano"]

        try:
            ano = AnoLetivo.objects.get(
                ano=ano_numero
            )

        except AnoLetivo.DoesNotExist:

            self.stdout.write(
                self.style.ERROR(
                    f"Ano letivo {ano_numero} não encontrado."
                )
            )
            return

        turmas = Turma.objects.filter(
            ano_letivo__isnull=True
        )

        avaliacoes = Avaliacao.objects.filter(
            ano_letivo__isnull=True
        )

        qtd_turmas = turmas.count()
        qtd_avaliacoes = avaliacoes.count()

        turmas.update(
            ano_letivo=ano
        )

        avaliacoes.update(
            ano_letivo=ano
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Turmas atualizadas: {qtd_turmas}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Avaliações atualizadas: {qtd_avaliacoes}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Ano letivo aplicado: {ano_numero}"
            )
        )