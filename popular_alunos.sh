#!/bin/bash
export DJANGO_SETTINGS_MODULE=plantao_pro.settings
ESCOLA_ID=1

echo "🚀 Iniciando população da base..."

python manage.py shell <<EOF
from home.models import *
from faker import Faker
from random import choice
import random

fake = Faker('pt_BR')

escola = Escola.objects.get(id=$ESCOLA_ID)

print('\\n📘 Criando disciplinas...')
disciplinas_nomes = ['Matemática', 'Português', 'Ciências', 'História']
disciplinas = []

for nome in disciplinas_nomes:
    d, _ = Disciplina.objects.get_or_create(nome=nome, escola=escola)
    disciplinas.append(d)

print('\\n🧑‍🏫 Criando professores...')
professores = []

for i in range(3):
    nome = fake.name()

    user = User.objects.create_user(
        username=f'prof_teste_{i}',
        password='123456',
        role='professor',
        escola=escola
    )

    prof = Docente.objects.create(
        nome=nome,
        cpf=fake.cpf(),
        nascimento=fake.date_of_birth(minimum_age=25, maximum_age=55),
        email=fake.email(),
        telefone=fake.phone_number(),
        cidade=fake.city(),
        estado=fake.estado_sigla(),
        cargo='Professor',
        formacao='Licenciatura',
        experiencia='5 anos',
        sexo=choice(['Masculino', 'Feminino']),
        ativo='Sim',
        user=user,
        escola=escola
    )

    professores.append(prof)

print('\\n🎒 Criando 20 alunos PADRONIZADOS...')
alunos = []

for i in range(1, 21):
    nome = f'ALUNO TESTE {i:02d}'

    aluno = Aluno.objects.create(
        nome=nome,
        data_nascimento=fake.date_of_birth(minimum_age=10, maximum_age=15),
        cpf=fake.cpf(),
        rg=fake.rg(),
        sexo=choice(['M', 'F']),
        nacionalidade='Brasileira',
        naturalidade=fake.city(),
        tipo_sanguineo='O+',
        rua=fake.street_name(),
        numero=str(fake.building_number()),
        cep=fake.postcode(),
        bairro=fake.bairro(),
        cidade=fake.city(),
        estado=fake.estado_sigla(),
        email=f'aluno{i}@teste.com',
        telefone=fake.phone_number(),
        escola=escola
    )

    alunos.append(aluno)
    print(f'  ➤ {nome}')

print('\\n🏫 Criando TURMA DE TESTE...')

turma = Turma.objects.create(
    nome='TURMA TESTE BOLETIM',
    turno='Manhã',
    ano=6,
    sala='101',
    descricao='Turma para teste de boletim',
    escola=escola
)

# 🔥 TODOS OS 20 NA MESMA TURMA
turma.alunos.set(alunos)

print(f'  ➤ Turma criada com {len(alunos)} alunos')

print('\\n📚 Criando TurmaDisciplina...')

for disciplina in disciplinas:
    prof = random.choice(professores)

    TurmaDisciplina.objects.create(
        turma=turma,
        disciplina=disciplina,
        professor=prof,
        escola=escola
    )

    print(f'  ➤ {disciplina.nome} → {prof.nome}')

print('\\n🎉 BASE PRONTA PARA TESTE DE BOLETIM!')
EOF

echo "✔️ Finalizado!"