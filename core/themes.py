def get_base_template(request):
    """
    Retorna qual base deve ser usada
    com base no tema da escola do usuário.
    """

    user = request.user

    if hasattr(user, "escola") and user.escola:
        if user.escola.tema == "nucleo":
            return "nucleo/base_nucleo.html"

    return "base.html"