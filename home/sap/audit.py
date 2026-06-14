from home.models import AuditLog


def registrar_auditoria(request, acao, obj=None, antes=None, depois=None):

    try:

        if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
            return

        AuditLog.objects.create(
            user=request.user,
            escola=getattr(request, "escola", None),
            acao=acao,
            modelo=obj.__class__.__name__ if obj else None,
            objeto_id=str(obj.id) if obj else None,
            antes=antes,
            depois=depois,
            ip=getattr(request, "META", {}).get("REMOTE_ADDR") if hasattr(request, "META") else None,
            user_agent=getattr(request, "META", {}).get("HTTP_USER_AGENT") if hasattr(request, "META") else None
        )

    except Exception:
        # 🔥 evita quebra do fluxo principal do sistema
        pass