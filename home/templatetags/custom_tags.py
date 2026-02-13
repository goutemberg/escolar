from django import template

register = template.Library()

@register.filter
def has_role(user, roles):
    """
    Verifica se o papel do usuário está dentro da lista de roles ou se é superusuário.
    Uso: {% if user|has_role:"diretor,coordenador" %}
    """
    if getattr(user, 'is_superuser', False):
        return True
    if not hasattr(user, 'role'):
        return False
    return user.role in [r.strip() for r in roles.split(',')]


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_item(dictionary, key):
    if dictionary and key in dictionary:
        return dictionary.get(key)
    return None


@register.filter
def get_nota_avaliacao(notas_dict, args):
    """
    Uso:
    {{ notas|get_nota_avaliacao:aluno.id|default:"" }}

    Mas como precisamos de dois argumentos (aluno_id e avaliacao_id),
    vamos usar formato:
    {{ notas|get_nota_avaliacao:"aluno_id|avaliacao_id" }}
    """

    try:
        aluno_id, avaliacao_id = args.split("|")

        aluno_id = int(aluno_id)
        avaliacao_id = int(avaliacao_id)

        return notas_dict.get(aluno_id, {}).get(avaliacao_id, "")
    except:
        return ""

