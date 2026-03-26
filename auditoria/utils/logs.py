# auditoria/utils/logs.py

from auditoria.models import LogAuditoria


def registrar_log(request, acao, descricao, modelo=None, objeto_id=None):

    LogAuditoria.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        acao=acao,
        descricao=descricao,
        modelo=modelo,
        objeto_id=objeto_id,
        ip=get_client_ip(request),
    )


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0]
    return request.META.get('REMOTE_ADDR')