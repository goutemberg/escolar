# auditoria/models.py

from django.db import models
from django.conf import settings


class LogAuditoria(models.Model):

    ACAO_CHOICES = [
        ('CREATE', 'Criação'),
        ('UPDATE', 'Atualização'),
        ('DELETE', 'Remoção'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('OUTRO', 'Outro'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    acao = models.CharField(max_length=20, choices=ACAO_CHOICES)

    modelo = models.CharField(max_length=100, null=True, blank=True)
    objeto_id = models.CharField(max_length=50, null=True, blank=True)

    descricao = models.TextField()

    ip = models.GenericIPAddressField(null=True, blank=True)

    data_hora = models.DateTimeField(auto_now_add=True)
    alteracoes = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.usuario} - {self.acao} - {self.data_hora}"