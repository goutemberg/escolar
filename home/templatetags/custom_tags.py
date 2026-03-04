from django import template

register = template.Library()

@register.filter
def has_role(user, roles):
    if getattr(user, 'is_superuser', False):
        return True
    if not hasattr(user, 'role'):
        return False
    return user.role in [r.strip() for r in roles.split(',')]

@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    # tenta int e string
    if key in dictionary:
        return dictionary.get(key)
    try:
        k_int = int(key)
        if k_int in dictionary:
            return dictionary.get(k_int)
    except Exception:
        pass
    k_str = str(key)
    return dictionary.get(k_str)


@register.filter
def get_nota_avaliacao(notas_dict, args):
    """
    {{ notas|get_nota_avaliacao:"aluno_id|avaliacao_id" }}
    Robustez: funciona se as chaves forem int ou str (nos dois níveis).
    """
    try:
        aluno_id_raw, avaliacao_id_raw = str(args).split("|")
        aluno_id_raw = aluno_id_raw.strip()
        avaliacao_id_raw = avaliacao_id_raw.strip()

        # tenta aluno_id como int e como str
        aluno_bucket = None
        try:
            aluno_id_int = int(aluno_id_raw)
        except:
            aluno_id_int = None

        if isinstance(notas_dict, dict):
            if aluno_id_int is not None and aluno_id_int in notas_dict:
                aluno_bucket = notas_dict.get(aluno_id_int)
            elif aluno_id_raw in notas_dict:
                aluno_bucket = notas_dict.get(aluno_id_raw)

        if not isinstance(aluno_bucket, dict):
            return ""

        # tenta avaliacao_id como int e como str
        try:
            avaliacao_id_int = int(avaliacao_id_raw)
        except:
            avaliacao_id_int = None

        if avaliacao_id_int is not None and avaliacao_id_int in aluno_bucket:
            v = aluno_bucket.get(avaliacao_id_int)
        else:
            v = aluno_bucket.get(avaliacao_id_raw)

        return "" if v is None else v

    except:
        return ""