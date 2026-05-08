from home.models import *
from faker import Faker
from random import choice
import random


print('\n🧹 Limpando alunos de teste antigos...')

Aluno.objects.filter(nome__startswith='ALUNO TESTE').delete()

def safe(val, max_len):
    return str(val)[:max_len] if val else ""

import uuid

def gerar_matricula_segura():
    return f"ALUNO{uuid.uuid4().hex[:10].upper()}"

fake = Faker('pt_BR')

ESCOLA_ID = 1

escola = Escola.objects.get(id=ESCOLA_ID)

print('\n📘 Criando disciplinas...')
disciplinas_nomes = ['Matemática', 'Português', 'Ciências', 'História']
disciplinas = []

for nome in disciplinas_nomes:
    d, _ = Disciplina.objects.get_or_create(nome=nome, escola=escola)
    disciplinas.append(d)

print('\n🧑‍🏫 Criando professores...')
professores = []

for i in range(3):
    nome = fake.name()

    user, _ = User.objects.get_or_create(
        username=f'prof_teste_{i}',
        defaults={
            'role': 'professor',
            'escola': escola
        }
    )
    user.set_password('123456')
    user.save()

    prof = Docente.objects.filter(user=user).first()

    if not prof:
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
            ativo=True,
            user=user,
            escola=escola
        )

    professores.append(prof)

print('\n🎒 Criando 20 alunos PADRONIZADOS com bulk_create...')

alunos_bulk = []

for i in range(1, 21):
    nome = f'ALUNO TESTE {i:02d}'

    aluno = Aluno(
        nome=safe(nome, 100),
        matricula=gerar_matricula_segura(),

        data_nascimento=fake.date_of_birth(minimum_age=10, maximum_age=15),

        cpf=safe(fake.cpf(), 14),
        rg=safe(fake.rg(), 20),

        sexo=choice(['M', 'F']),

        nacionalidade='Brasileira',
        naturalidade=safe(fake.city(), 50),

        tipo_sanguineo='O+',

        rua=safe(fake.street_name(), 100),
        numero=safe(fake.building_number(), 10),

        cep=safe(fake.postcode(), 10),
        bairro=safe(fake.bairro(), 50),
        cidade=safe(fake.city(), 50),

        estado=safe(fake.estado_sigla(), 2),

        email=f'aluno{i}@teste.com',

        telefone=safe(fake.phone_number(), 20),

        escola=escola
    )

    alunos_bulk.append(aluno)


# 🔥 cria tudo sem chamar save()
Aluno.objects.bulk_create(alunos_bulk)

# 🔥 busca de volta os alunos criados
alunos = list(
    Aluno.objects.filter(email__startswith='aluno', escola=escola)
    .order_by('-id')[:20]
)

for aluno in alunos:
    print(f'  ➤ {aluno.nome}')

print('\n🏫 Criando TURMA DE TESTE...')

turma, _ = Turma.objects.get_or_create(
    nome='TURMA TESTE BOLETIM',
    turno='Manhã',
    ano=6,
    escola=escola,
    defaults={
        'sala': '101',
        'descricao': 'Turma para teste de boletim'
    }
)

# 🔥 adiciona alunos na turma
turma.alunos.set(alunos)

print(f'  ➤ Turma criada com {len(alunos)} alunos')

print('\n📚 Criando TurmaDisciplina...')

for disciplina in disciplinas:
    prof = random.choice(professores)

    TurmaDisciplina.objects.get_or_create(
        turma=turma,
        disciplina=disciplina,
        professor=prof,
        escola=escola
    )

    print(f'  ➤ {disciplina.nome} → {prof.nome}')

print('\n🎉 BASE PRONTA PARA TESTE DE BOLETIM!')