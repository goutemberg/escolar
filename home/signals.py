from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Docente
from django.dispatch import receiver
from .models import User, Docente

@receiver(post_save, sender=Docente)
def preencher_escola_docente(sender, instance, created, **kwargs):
    if created and instance.user and instance.user.escola and not instance.escola:
        instance.escola = instance.user.escola
        instance.save()

