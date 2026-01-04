from django.http import HttpResponseForbidden

from functools import wraps
from django.http import HttpResponseForbidden

def role_required(roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):

            user = request.user

            # 1️⃣ valida papel
            if not hasattr(user, 'role') or user.role not in roles:
                return HttpResponseForbidden("Acesso negado")

            # 2️⃣ NÃO faça filtro por escola aqui
            # escola é responsabilidade da VIEW

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator

