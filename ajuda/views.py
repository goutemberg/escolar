from django.http import JsonResponse
from .models import VideoAjuda


def buscar_video_ajuda(request):
    modulo = request.GET.get("modulo")

    if not modulo:
        return JsonResponse({"erro": "Módulo não informado"}, status=400)

    video = VideoAjuda.objects.filter(
        modulo=modulo,
        ativo=True
    ).order_by("-id").first()

    if not video:
        return JsonResponse({"erro": "Nenhum vídeo encontrado"}, status=404)

    return JsonResponse({
        "titulo": video.titulo,
        "url": video.url,
        "descricao": video.descricao,
        "playlist_url": video.playlist_url or ""
    })