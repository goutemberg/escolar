from datetime import datetime

def gerar_matricula_unica():
    from .models import Aluno
    prefixo = "ALU"
    ano = datetime.now().year
    base = f"{prefixo}{ano}"

    ultimo_aluno = (
        Aluno.objects.filter(matricula__startswith=base)
        .order_by('-id')
        .first()
    )
    numero = 1

    if ultimo_aluno:
        try:
            numero = int(ultimo_aluno.matricula[-4:]) + 1
        except:
            pass

    nova_matricula = f"{base}{str(numero).zfill(4)}"
    return nova_matricula