from django.http import JsonResponse
from home.sap.context import set_current_request, clear_current_request


class SAPMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        request.is_locked = False

        from home.models import AnoLetivo

        ano = AnoLetivo.objects.filter(ativo=True).first()

        if ano and ano.encerrado:

            request.is_locked = True

            if request.method in ["POST", "PUT", "PATCH", "DELETE"]:

                if "/admin/" not in request.path:

                    return JsonResponse({
                        "error": "Ano letivo encerrado"
                    }, status=403)

        return self.get_response(request)


class SAPContextMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        set_current_request(request)

        try:
            response = self.get_response(request)
            return response

        finally:
            
            clear_current_request()