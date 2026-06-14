from home.utils import get_escola_ativa
from home.models import AnoLetivo
from django.http import JsonResponse
from home.utils import registrar_auditoria


class EscolaAtivaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # =====================================================
        # 1. DEFINIÇÃO DA ESCOLA ATIVA (MULTI-ESCOLA)
        # =====================================================
        if request.user.is_authenticated:
            escola = get_escola_ativa(request)

            if not escola:
                vinculo = request.user.userescola_set.first()

                if vinculo:
                    request.session["escola_id"] = vinculo.escola.id
                    request.session.save()
                    escola = vinculo.escola

            request.escola = escola

        else:
            request.escola = None

        # =====================================================
        # 2. BLOQUEIO DE ANO LETIVO ENCERRADO (SAP MODE)
        # =====================================================

        ano_encerrado = AnoLetivo.objects.filter(
            encerrado=True
        ).order_by("-ano").first()

        if ano_encerrado:

            path = request.path

            # 🔓 ROTAS SEMPRE LIBERADAS
            rotas_liberadas = [
                "/admin/",
                "/logout/",
                "/login/",
                "/fechamento/",
            ]

            # ROTAS CRÍTICAS
            rotas_criticas = [
    "/notas/",
    "/avaliacoes/",
    "/lancar/",
    "/turmas/",
    "/chamada/",
    "/diario/",
    "/registro-pedagogico/",
    "/disciplinas/",

    "/salvar-categoria-avaliacao/",
    "/editar-categoria/",
    "/excluir-categoria/",

    "/salvar-item-avaliacao/",
    "/editar-item/",
    "/excluir-item/",
]

            # =================================================
            # NÃO BLOQUEIA ROTAS LIBERADAS
            # =================================================
            if any(r in path for r in rotas_liberadas):
                return self.get_response(request)

            # =================================================
            # BLOQUEIA SOMENTE ESCRITA
            # =================================================
            if request.method in ["POST", "PUT", "PATCH", "DELETE"]:

                if any(r in path for r in rotas_criticas):

                    return JsonResponse(
    {
        "success": False,
        "error": (
            f"Ano letivo {ano_encerrado.ano} "
            "encerrado. Operações bloqueadas."
        )
    },
    status=403
)

        # =====================================================
        # 3. CONTINUA FLUXO NORMAL
        # =====================================================
        return self.get_response(request)


class AuditMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        # só ações de escrita
        if (
            request.user.is_authenticated
            and request.method in ["POST", "PUT", "PATCH", "DELETE"]
        ):

            path = request.path

            modulos = [
                "/notas/",
                "/avaliacoes/",
                "/lancar/",
                "/turmas/",
                "/chamada/",
                "/diario/",
                "/registro-pedagogico/",
                "/disciplinas/"
            ]

            if any(m in path for m in modulos):

                registrar_auditoria(
                    request=request,
                    acao="AUTO_ACTION",
                    obj=None,
                    antes=None,
                    depois={
                        "path": path,
                        "method": request.method
                    }
                )

        return response