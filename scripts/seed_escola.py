import os
import sys
import random
from random import choice, randint

# 🔥 PATH DO PROJETO
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# 🔥 SETTINGS
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plantao_pro.settings.base")

import django
django.setup()

# 🔥 MODELS
from home.models import Escola, Disciplina, Docente, Aluno, Turma, TurmaDisciplina, User

from faker import Faker


# ========================
# 🔥 GERADOR DE CPF SEGURO
# ========================
def gerar_cpf():
    while True:
        cpf = "".join([str(random.randint(0, 9)) for _ in range(11)])
        if cpf and not Docente.objects.filter(cpf=cpf).exists() and not Aluno.objects.filter(cpf=cpf).exists():
            return cpf


def run(escola_id=1, total_alunos=50, reset=False):
    fake = Faker("pt_BR")

    escola = Escola.objects.get(id=escola_id)

    print(f"\n🚀 Seed iniciada para escola {escola_id}")

    # ========================
    # RESET
    # ========================
    if reset:
        print("🧨 Resetando dados...")
        TurmaDisciplina.objects.filter(escola=escola).delete()
        Turma.objects.filter(escola=escola).delete()
        Aluno.objects.filter(escola=escola).delete()
        Docente.objects.filter(escola=escola).delete()
        Disciplina.objects.filter(escola=escola).delete()

    # ========================
    # DISCIPLINAS
    # ========================
    print("\n📘 Criando disciplinas...")

    disciplinas_nomes = ["Matemática", "Português", "Ciências", "História"]
    disciplinas = []

    for nome in disciplinas_nomes:
        d, _ = Disciplina.objects.get_or_create(nome=nome, escola=escola)
        disciplinas.append(d)
        print(f"  ➤ {nome}")

    # ========================
    # PROFESSORES
    # ========================
    print("\n🧑‍🏫 Criando professores...")

    professores = []

    for i in range(5):
        username = f"prof_{escola_id}_{i}"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "role": "professor",
                "escola": escola,
            },
        )

        if created:
            user.set_password("123456")
            user.save()

        cpf = gerar_cpf()

        prof, _ = Docente.objects.get_or_create(
            user=user,
            defaults={
                "nome": fake.name(),
                "cpf": cpf,
                "nascimento": fake.date_of_birth(minimum_age=25, maximum_age=55),
                "email": fake.email(),
                "telefone": fake.phone_number(),
                "cep": fake.postcode(),
                "endereco": fake.street_name(),
                "numero": str(fake.building_number()),
                "bairro": fake.city(),
                "cidade": fake.city(),
                "estado": fake.estado_sigla(),
                "cargo": "Professor",
                "formacao": "Licenciatura",
                "experiencia": "5 anos",
                "sexo": choice(["Masculino", "Feminino"]),
                "ativo": True,
                "escola": escola,
            },
        )

        professores.append(prof)
        print(f"  ➤ {prof.nome}")

    # ========================
    # ALUNOS
    # ========================
    print(f"\n🎒 Criando {total_alunos} alunos...")

    alunos = []

    for _ in range(total_alunos):
        cpf = gerar_cpf()

        aluno = Aluno.objects.create(
            nome=fake.name(),
            data_nascimento=fake.date_of_birth(minimum_age=10, maximum_age=18),
            cpf=cpf,
            rg=fake.rg(),
            sexo=choice(["M", "F"]),
            nacionalidade="Brasileira",
            naturalidade=fake.city(),
            tipo_sanguineo=choice(["A+", "O+", "B+", "AB+"]),
            rua=fake.street_name(),
            numero=str(fake.building_number()),
            cep=fake.postcode(),
            bairro=fake.city(),
            cidade=fake.city(),
            estado=fake.estado_sigla(),
            email=fake.email(),
            telefone=fake.phone_number(),
            escola=escola,
        )
        alunos.append(aluno)

    print("  ➤ Alunos criados!")

    # ========================
    # TURMAS
    # ========================
    print("\n🏫 Criando turmas...")

    turmas_info = [
        ("6º Ano A", "Manhã", 6),
        ("6º Ano B", "Tarde", 6),
        ("7º Ano A", "Manhã", 7),
        ("7º Ano B", "Tarde", 7),
    ]

    turmas = []

    for nome, turno, ano in turmas_info:
        turma, _ = Turma.objects.get_or_create(
            nome=nome,
            escola=escola,
            defaults={
                "turno": turno,
                "ano": ano,
                "sala": str(randint(1, 20)),
                "descricao": "Turma automática",
            },
        )

        turma.alunos.set(random.sample(alunos, min(25, len(alunos))))

        turmas.append(turma)

        print(f"  ➤ {turma.nome}")

    # ========================
    # TURMA DISCIPLINA
    # ========================
    print("\n📚 Criando vínculos TurmaDisciplina...")

    for turma in turmas:
        for disciplina in disciplinas:
            TurmaDisciplina.objects.get_or_create(
                turma=turma,
                disciplina=disciplina,
                defaults={
                    "professor": choice(professores),
                    "escola": escola,
                },
            )

    print("\n🎉 Seed finalizada com sucesso!\n")


if __name__ == "__main__":
    run(escola_id=2, total_alunos=200, reset=True)