from django.core.management.base import BaseCommand
from home.models import User, UserEscola


class Command(BaseCommand):
    help = 'Migra dados de User.escola para UserEscola'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Iniciando migração User → UserEscola...")

        total = 0

        for user in User.objects.all():

            if user.escola:
                obj, created = UserEscola.objects.get_or_create(
                    user=user,
                    escola=user.escola
                )

                if created:
                    total += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Migração concluída! {total} vínculos criados."
        ))