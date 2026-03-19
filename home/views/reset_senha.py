from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from home.models import User, PasswordResetToken
import re


# 🔐 Validador de senha forte
def validar_senha_forte(senha):
    if len(senha) < 8:
        return "A senha deve ter pelo menos 8 caracteres"
    if not re.search(r"[A-Z]", senha):
        return "A senha deve conter letra maiúscula"
    if not re.search(r"[a-z]", senha):
        return "A senha deve conter letra minúscula"
    if not re.search(r"\d", senha):
        return "A senha deve conter número"
    return None


def nova_senha(request, token):

    try:
        token_obj = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        messages.error(request, "Token inválido")
        return redirect("login")

    # 🔥 verificar expiração (CORRIGIDO: faltava return)
    if token_obj.is_expired():
        token_obj.delete()
        messages.error(request, "Token expirado. Solicite novamente.")
        return redirect("reset_senha:reset_senha")

    if request.method == "POST":
        senha = request.POST.get("senha")

        if not senha:
            messages.error(request, "Informe uma senha válida.")
            return redirect(request.path)

        # 🔐 valida senha forte
        erro = validar_senha_forte(senha)
        if erro:
            messages.error(request, erro)
            return redirect(request.path)

        user = token_obj.user

        # 🔥 invalida TODOS tokens do usuário (segurança)
        PasswordResetToken.objects.filter(user=user).delete()

        user.set_password(senha)
        user.senha_temporaria = False
        user.save()

        # 🔥 LOGIN AUTOMÁTICO (grande melhoria)
        login(request, user)

        messages.success(request, "Senha redefinida com sucesso!")
        return redirect("index")  # 🔥 melhor UX (não volta pro login)

    return render(request, "pages/trocar_senha.html", {
        "token": token
    })


def reset_senha(request):

    if request.method == "POST":
        identificador = request.POST.get("cpf")

        print("CPF recebido:", identificador)  # DEBUG

        if not identificador:
            messages.error(request, "Informe o CPF")
            return redirect("reset_senha:reset_senha")

        # 🔥 normaliza CPF (IMPORTANTE)
        identificador = identificador.replace('.', '').replace('-', '').replace('/', '')

        try:
            user = User.objects.get(cpf=identificador)
            print("Usuário encontrado:", user)
        except User.DoesNotExist:
            print("Usuário NÃO encontrado")
            messages.error(request, "Usuário não encontrado")
            return redirect("reset_senha:reset_senha")

        # 🔥 limpar tokens antigos
        PasswordResetToken.objects.filter(user=user).delete()

        token = PasswordResetToken.objects.create(user=user)

        reset_link = request.build_absolute_uri(
            f"/reset_senha/nova-senha/{token.token}/"
        )

        print(f"LINK RESET: {reset_link}")

        # 🔥 redireciona corretamente (já estava certo)
        return redirect("reset_senha:nova_senha", token=token.token)

    return render(request, "pages/reset_senha.html")