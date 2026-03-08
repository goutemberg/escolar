from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
from .forms import UserCreationNoPasswordForm

from .models import Escola, User


# ============================
#  ESCOLA ADMIN
# ============================
@admin.register(Escola)
class EscolaAdmin(admin.ModelAdmin):
    list_display = ("codigo_cliente", "nome", "cnpj", "cidade", "estado", "tema")
    search_fields = ("codigo_cliente", "nome", "cnpj")
    ordering = ("nome",)
    list_editable = ("tema",)
    readonly_fields = ("codigo_cliente",)

    fields = (
        "codigo_cliente",
        "nome",
        "cnpj",
        "telefone",
        "email",
        "endereco",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
        "site",
        "cep",
        "tema",
    )


# ============================
#  USER ADMIN PERSONALIZADO
# ============================
@admin.register(User)
class CustomUserAdmin(DjangoUserAdmin):

    add_form = UserCreationNoPasswordForm
    form = UserCreationNoPasswordForm

    list_display = (
        "username", "cpf", "first_name", "last_name",
        "role", "escola", "is_active", "reset_password_button"
    )
    list_filter = ("role", "escola", "is_staff")
    search_fields = ("username", "cpf", "first_name", "last_name", "email")
    ordering = ("cpf",)

    fieldsets = (
        (None, {"fields": ("cpf", "username", "password")}),
        ("Informações pessoais", {"fields": ("first_name", "last_name", "email")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Outros", {"fields": ("role", "escola")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("cpf", "username", "first_name", "last_name", "email", "role", "escola"),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("cpf", "password")
        return ("password",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "escola":
            kwargs["queryset"] = Escola.objects.order_by("nome")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_password("123456")
            obj.senha_temporaria = True
        super().save_model(request, obj, form, change)

    def reset_password_button(self, obj):
        return format_html(
            f'<a class="button" href="reset-password/{obj.id}">Resetar senha</a>'
        )
    reset_password_button.short_description = "Resetar senha"
    reset_password_button.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "reset-password/<int:user_id>",
                self.admin_site.admin_view(self.reset_password_action),
                name="reset-user-password"
            ),
        ]
        return custom_urls + urls

    def reset_password_action(self, request, user_id):
        user = User.objects.get(id=user_id)
        user.set_password("123456")
        user.senha_temporaria = True
        user.save()
        messages.success(request, f"A senha do usuário {user.username} foi resetada para 123456.")
        return redirect(f"/admin/home/user/{user_id}/change/")