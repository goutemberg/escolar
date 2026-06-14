from home.models import AnoLetivo

def escola_no_contexto(request):
    return {
        'escola_vinculada': getattr(request.user, 'escola', None) if request.user.is_authenticated else None
    }


def ano_atual(request):
    ano = AnoLetivo.objects.filter(ativo=True).first()

    return {
        "ano_atual": ano
    }
