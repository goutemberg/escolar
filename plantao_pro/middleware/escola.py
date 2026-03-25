from home.utils import get_escola_ativa


from home.utils import get_escola_ativa

class EscolaAtivaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:
            escola = get_escola_ativa(request)

            if not escola:
                # 🔥 fallback automático
                vinculo = request.user.userescola_set.first()
                if vinculo:
                    request.session["escola_id"] = vinculo.escola.id
                    request.session.save()
                    escola = vinculo.escola

            request.escola = escola
        else:
            request.escola = None

        return self.get_response(request)