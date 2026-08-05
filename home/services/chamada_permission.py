from datetime import timedelta

from django.utils import timezone

from home.models import Docente


def pode_excluir_chamada(user, chamada, config):

    # ==========================================
    # PARÂMETROS DO SISTEMA
    # ==========================================

    if not config.permite_exclusao:
        return False

    # ==========================================
    # SUPERUSUÁRIO
    # ==========================================

    if user.is_superuser:
        return True

    # ==========================================
    # DIRETOR (TEMPORÁRIO)
    # ==========================================

    if user.role == "diretor":
        return True

    # ==========================================
    # USUÁRIO QUE CRIOU A CHAMADA
    # ==========================================

    if chamada.criado_por_id == user.id:
        return True

    # ==========================================
    # PROFESSOR DA CHAMADA
    # ==========================================

    professor = Docente.objects.filter(
        user=user,
        escola=chamada.escola,
    ).first()

    if professor and chamada.professor_id == professor.id:
        return True

    # ==========================================
    # APENAS O CRIADOR
    # ==========================================

    if config.apenas_criador_exclui and chamada.criado_por_id != user.id:
        return False

    # ==========================================
    # LIMITE DE TEMPO
    # ==========================================

    if config.limite_exclusao_horas is not None:

        data_limite = chamada.criado_em + timedelta(hours=config.limite_exclusao_horas)

        if timezone.now() > data_limite:
            return False

    return False
