#!/bin/bash
ESCOLA_ID=1

echo "🚀 Iniciando população da base..."

python3 manage.py shell <<EOF
from home.models import *
from faker import Faker
from random import choice, randint
import random

fake = Faker("pt_BR")

escola = Escola.objects.get(id=$ESCOLA_ID)

print("📘 Criando disciplinas...")
disciplinas_nomes = ["Matemática", "Português", "Ciências", "História"]
disciplinas = []

for nome in disciplinas_nomes:
    d, _ = Disciplina.objects.get_or_create(nome=nome, escola=escola)
    disciplinas.append(d)
    print(f"  ➤ {nome}")

print("\n🧑‍🏫 Criando professores...")
professores = []
for i in range(5):
    nome = fake.name()
    user = User.objects.create_user(
        username=f"prof{i}",
        password="123456",
        first_name=nome.split()[0],
        last_name=" ".join(nome.split()[1:]),
        role="professor",
        escola=escola
    )

    prof = Docente.objects.create(
        nome=nome,
        cpf=fake.cpf(),
        nascimento=fake.date_of_birth(minimum_age=25, maximum_age=55),
        email=fake.email(),
        telefone=fake.phone_number(),
        cep=fake.postcode(),
        endereco=fake.street_name(),
        numero=str(fake.building_number()),
        bairro=fake.bairro(),
        cidade=fake.city(),
        estado=fake.estado_sigla(),
        cargo="Professor",
        formacao="Licenciatura",
        experiencia="5 anos",
        sexo=choice(["Masculino", "Feminino"]),
        ativo="Sim",
        user=user,
        escola=escola
    )

    # Atribui disciplinas aleatórias
    prof.disciplinas.set(random.sample(disciplinas, randint(1, 3)))
    prof.save()

    professores.append(prof)
    print(f"  ➤ {nome}")

print("\n🎒 Criando 100 alunos...")
alunos = []
for i in range(100):
    nome = fake.name()
    aluno = Aluno.objects.create(
        nome=nome,
        data_nascimento=fake.date_of_birth(minimum_age=10, maximum_age=18),
        cpf=fake.cpf(),
        rg=fake.rg(),
        sexo=choice(["M", "F"]),
        nacionalidade="Brasileira",
        naturalidade=fake.city(),
        tipo_sanguineo=choice(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]),
        rua=fake.street_name(),
        numero=str(fake.building_number()),
        cep=fake.postcode(),
        bairro=fake.bairro(),
        cidade=fake.city(),
        estado=fake.estado_sigla(),
        email=fake.email(),
        telefone=fake.phone_number(),
        escola=escola
    )
    alunos.append(aluno)

print("  ➤ 100 alunos criados!")

print("\n🏫 Criando turmas e distribuindo alunos / professores...")
turmas_info = [
    ("6º Ano A", "Manhã", 6),
    ("6º Ano B", "Tarde", 6),
    ("7º Ano A", "Manhã", 7),
    ("7º Ano B", "Tarde", 7),
]

turmas = []

for nome, turno, ano in turmas_info:
    turma = Turma.objects.create(
        nome=nome,
        turno=turno,
        ano=ano,
        sala=str(randint(1, 20)),
        descricao="Turma gerada automaticamente",
        escola=escola
    )

    # Distribui 25 alunos por turma
    turma_alunos = random.sample(alunos, 25)
    turma.alunos.set(turma_alunos)

    # Atribui 1–2 professores por turma
    turma_professores = random.sample(professores, randint(1, 2))
    turma.professores.set(turma_professores)

    turmas.append(turma)
    print(f"  ➤ Turma {nome} criada com {len(turma_alunos)} alunos")

print("\n📚 Criando relações TurmaDisciplina...")
for turma in turmas:
    for disciplina in disciplinas:
        prof = choice(professores)  # professor aleatório
        TurmaDisciplina.objects.create(
            turma=turma,
            disciplina=disciplina,
            professor=prof,
            escola=escola
        )
        print(f"  ➤ {turma.nome} - {disciplina.nome} → {prof.nome}")

print("\n🎉 População concluída com sucesso!")
EOF

echo "✔️ Finalizado!"
