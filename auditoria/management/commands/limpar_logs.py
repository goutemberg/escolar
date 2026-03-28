# auditoria/management/commands/limpar_logs.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from auditoria.models import LogAuditoria


class Command(BaseCommand):
    help = "Remove logs de auditoria antigos"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=90,
            help='Quantidade de dias para manter os logs (default: 90)'
        )

    def handle(self, *args, **options):

        dias = options['dias']
        limite = timezone.now() - timedelta(days=dias)

        logs_antigos = LogAuditoria.objects.filter(data_hora__lt=limite)

        total = logs_antigos.count()

        logs_antigos.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"{total} logs antigos removidos (>{dias} dias)"
            )
        )