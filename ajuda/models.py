from django.db import models


class VideoAjuda(models.Model):
    TIPO_CHOICES = (
        ("video", "Vídeo"),
        ("playlist", "Playlist"),
    )

    titulo = models.CharField(max_length=200)
    url = models.URLField()
    modulo = models.CharField(max_length=100)  # ex: "aluno"
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default="video")

    
    playlist_url = models.URLField(blank=True, null=True)

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.modulo} - {self.titulo}"