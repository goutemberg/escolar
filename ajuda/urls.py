from django.urls import path
from .views import buscar_video_ajuda

urlpatterns = [
    path("buscar/", buscar_video_ajuda, name="buscar_video_ajuda"),
]