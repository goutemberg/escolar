from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from home.models import Nota
from home.sap.audit import SAPAuditCore
from home.sap.context import get_current_request


@receiver(post_save, sender=Nota)
def audit_nota_save(sender, instance, created, **kwargs):

    request = get_current_request()

    SAPAuditCore.log(
        request=request,
        acao="CREATE_NOTA" if created else "UPDATE_NOTA",
        modulo="NOTA",
        objeto=instance,
        depois={
            "valor": str(instance.valor) if instance.valor is not None else None,
            "conceito": instance.conceito
        }
    )


@receiver(pre_delete, sender=Nota)
def audit_nota_delete(sender, instance, **kwargs):

    request = get_current_request()

    SAPAuditCore.log(
        request=request,
        acao="DELETE_NOTA",
        modulo="NOTA",
        objeto=instance,
        antes={
            "valor": str(instance.valor) if instance.valor is not None else None,
            "conceito": instance.conceito
        }
    )