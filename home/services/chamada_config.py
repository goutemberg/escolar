from django.conf import settings


class ConfiguracaoChamada:

    def __init__(self, escola):
        self.escola = escola

    @property
    def permite_exclusao(self):
        return getattr(
            settings,
            "CHAMADA_PERMITE_EXCLUSAO",
            True,
        )

    @property
    def limite_exclusao_horas(self):
        return getattr(
            settings,
            "CHAMADA_LIMITE_EXCLUSAO_HORAS",
            None,
        )

    @property
    def apenas_criador_exclui(self):
        return getattr(
            settings,
            "CHAMADA_APENAS_CRIADOR_EXCLUI",
            False,
        )
