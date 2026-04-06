from django.contrib import admin
from .models import VideoAjuda


@admin.register(VideoAjuda)
class VideoAjudaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "modulo", "tipo", "ativo", "criado_em")
    list_filter = ("modulo", "tipo", "ativo")
    search_fields = ("titulo", "descricao", "modulo")