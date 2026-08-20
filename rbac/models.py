from django.contrib.auth.models import Group
from django.db import models


class Role(models.Model):
    """
    Informações complementares aos perfis (Groups) do Django.
    """

    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name="role",
    )

    description = models.TextField(
        blank=True,
        verbose_name="Descrição",
    )

    icon = models.CharField(
        max_length=50,
        default="bi-person-badge-fill",
        verbose_name="Ícone",
    )

    color = models.CharField(
        max_length=20,
        default="primary",
        verbose_name="Cor",
    )

    is_system = models.BooleanField(
        default=False,
        verbose_name="Perfil do Sistema",
    )

    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordem de Exibição",
    )

    class Meta:
        ordering = ["display_order", "group__name"]
        verbose_name = "Perfil"
        verbose_name_plural = "Perfis"

    def __str__(self):
        return self.group.name
