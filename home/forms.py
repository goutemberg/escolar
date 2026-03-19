from django import forms
from .models import Escola
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import User
from django.contrib.auth.forms import UserChangeForm


class UserCreationNoPasswordForm(forms.ModelForm):
    """simples para criar usuário sem pedir senha."""

    class Meta:
        model = User
        fields = ("cpf", "username", "first_name", "last_name", "email", "role", "escola")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password("123456")  # senha padrão
        user.senha_temporaria = True
        if commit:
            user.save()
        return user
    

class UserChangeCustomForm(UserChangeForm):
    password = None  # remove campo senha

    class Meta:
        model = User
        fields = "__all__"


class EscolaForm(forms.ModelForm):
    class Meta:
        model = Escola  # O modelo que o formulário representa
        fields = '__all__'

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj')
        if cnpj:
            # Remover a máscara do CNPJ caso tenha sido inserida
            cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')
        return cnpj