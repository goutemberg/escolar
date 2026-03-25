from home.utils import get_escola_ativa


class EscolaAtivaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:
            request.escola = get_escola_ativa(request)
        else:
            request.escola = None

        return self.get_response(request)