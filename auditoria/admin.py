# auditoria/admin.py

from django.contrib import admin
from .models import LogAuditoria


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'acao', 'modelo', 'objeto_id', 'data_hora')
    list_filter = ('acao', 'modelo', 'data_hora')
    search_fields = ('descricao', 'usuario__username')
    ordering = ('-data_hora',)