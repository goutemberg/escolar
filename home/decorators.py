
from functools import wraps
from django.shortcuts import redirect

def role_required(roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):

            # NOVO (multi-role)
            if request.user.roles.filter(nome__in=roles).exists():
                return view_func(request, *args, **kwargs)

            # ANTIGO (fallback)
            if request.user.role in roles:
                return view_func(request, *args, **kwargs)

            return redirect('sem_permissao')

        return wrapper
    return decorator

