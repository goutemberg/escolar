# auditoria/signals.py

from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from auditoria.models import LogAuditoria
from auditoria.middleware import get_current_user
from auditoria.utils.serializer import model_to_dict


# 🔹 MODELS QUE NÃO DEVEM SER LOGADOS
EXCLUDED_MODELS = [
    'LogAuditoria',
    'Session',
    'ContentType',
    'Permission',
]


# 🔹 APPS QUE NÃO DEVEM SER LOGADOS
EXCLUDED_APPS = [
    'admin',
    'sessions',
    'contenttypes',
    'auth',
]


def model_name(instance):
    return instance.__class__.__name__


# 🔹 FUNÇÃO CENTRAL DE FILTRO
def should_skip(sender):
    app_label = sender._meta.app_label
    model_name_sender = sender.__name__

    if model_name_sender in EXCLUDED_MODELS:
        return True

    if app_label in EXCLUDED_APPS:
        return True

    return False


# 🔹 CAPTURA ESTADO ANTES
@receiver(pre_save)
def capture_old_data(sender, instance, **kwargs):

    if should_skip(sender):
        return

    if not instance.pk:
        instance._old_data = None
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        instance._old_data = model_to_dict(old_instance)
    except sender.DoesNotExist:
        instance._old_data = None


# 🔹 SALVA LOG COM DIFERENÇA
@receiver(post_save)
def log_save(sender, instance, created, **kwargs):

    if should_skip(sender):
        return

    usuario = get_current_user()

    new_data = model_to_dict(instance)
    old_data = getattr(instance, '_old_data', None)

    alteracoes = {}

    if old_data:
        for key in new_data:
            if old_data.get(key) != new_data.get(key):
                alteracoes[key] = {
                    "antes": old_data.get(key),
                    "depois": new_data.get(key)
                }

    # 🔥 evita log de update sem alteração
    if not created and not alteracoes:
        return

    acao = 'CREATE' if created else 'UPDATE'

    LogAuditoria.objects.create(
        usuario=usuario if usuario and usuario.is_authenticated else None,
        acao=acao,
        modelo=model_name(instance),
        objeto_id=str(instance.pk),
        descricao=f"{acao} em {model_name(instance)} (ID: {instance.pk})",
        alteracoes=alteracoes if alteracoes else None
    )


# 🔹 DELETE
@receiver(post_delete)
def log_delete(sender, instance, **kwargs):

    if should_skip(sender):
        return

    usuario = get_current_user()

    LogAuditoria.objects.create(
        usuario=usuario if usuario and usuario.is_authenticated else None,
        acao='DELETE',
        modelo=model_name(instance),
        objeto_id=str(instance.pk),
        descricao=f"DELETE em {model_name(instance)} (ID: {instance.pk})"
    )