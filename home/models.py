from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import uuid
from .utils import gerar_matricula_unica


# ================================================
#  ESCOLA
# ================================================
class Escola(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    cnpj = models.CharField(
        max_length=18,
        unique=True,
        validators=[RegexValidator(regex=r'^\d{14}$', message='CNPJ inválido')]
    )
    telefone = models.CharField(
        max_length=16,
        validators=[RegexValidator(
            regex=r'^\(?\d{2}\)?[\s-]?\d{4,5}-?\d{4}$',
            message='Telefone inválido'
        )]
    )
    email = models.EmailField(max_length=100)
    endereco = models.CharField(max_length=255)
    numero = models.CharField(max_length=10)
    complemento = models.CharField(max_length=255, blank=True, null=True)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    site = models.CharField(max_length=200, blank=True, null=True)
    cep = models.CharField(max_length=9, default='00000000')

    def clean(self):
        if self.cnpj:
            self.cnpj = self.cnpj.replace('.', '').replace('/', '').replace('-', '')
        if Escola.objects.filter(cnpj=self.cnpj).exclude(id=self.id).exists():
            raise ValidationError("Este CNPJ já está cadastrado no sistema.")

    def __str__(self):
        return self.nome


# ================================================
#  USER CUSTOMIZADO
# ================================================
class User(AbstractUser):
    ROLE_CHOICES = [
        ('professor', 'Professor'),
        ('diretor', 'Diretor'),
        ('coordenador', 'Coordenador'),
        ('secretaria', 'Secretária'),
        ('responsavel', 'Responsável'),
    ]

    cpf = models.CharField(
        max_length=11,
        unique=True,
        null=True,
        blank=True,
        help_text="CPF do usuário (apenas números)"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='responsavel',
    )

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    senha_temporaria = models.BooleanField(default=False)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["cpf", "first_name", "last_name"]

    def __str__(self):
        return f"{self.username} ({self.cpf})"


# ================================================
#  DISCIPLINA
# ================================================
class Disciplina(models.Model):
    nome = models.CharField(max_length=100)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome


# ================================================
#  DOCENTE
# ================================================
class Docente(models.Model):
    nome = models.CharField(max_length=100, default='')
    cpf = models.CharField(max_length=14, unique=True, default='')
    nascimento = models.DateField(default='1900-01-01')
    email = models.EmailField(default='')
    telefone = models.CharField(max_length=20, default='')
    telefone_secundario = models.CharField(max_length=20, blank=True, default='')

    cep = models.CharField(max_length=9, default='00000-000')
    endereco = models.CharField(max_length=100, default='')
    numero = models.CharField(max_length=10, default='')
    complemento = models.CharField(max_length=100, blank=True, default='')
    bairro = models.CharField(max_length=50, default='')
    cidade = models.CharField(max_length=50, default='')
    estado = models.CharField(max_length=2, default='PE')

    cargo = models.CharField(max_length=50, default='Professor')
    grau_instrucao = models.CharField(max_length=30, default='')

    formacao = models.CharField(max_length=100, default='')
    experiencia = models.TextField(default='')

    sexo = models.CharField(max_length=20, default='Masculino')

    # 🔑 AGORA SIM
    ativo = models.BooleanField(default=True)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="docente"
    )

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name='docentes'
    )

    def __str__(self):
        return self.nome


# ================================================
#  FUNCIONÁRIO
# ================================================
class Funcionario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cargo = models.CharField(max_length=100)
    departamento = models.CharField(max_length=100)
    data_admissao = models.DateField()
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.cargo}"


# ================================================
#  ALUNO
# ================================================
class Aluno(models.Model):
    matricula = models.CharField(max_length=20, unique=True, default=gerar_matricula_unica)
    nome = models.CharField(max_length=255, default='')
    data_nascimento = models.DateField(blank=True, null=True)
    #cpf = models.CharField(max_length=14, default='')
    cpf = models.CharField(max_length=14, null=True, blank=True, default="")
    rg = models.CharField(max_length=20, blank=True, null=True, default='')
    sexo = models.CharField(max_length=10, default='')
    nacionalidade = models.CharField(max_length=50, default='')
    naturalidade = models.CharField(max_length=50, default='')
    certidao_numero = models.CharField(max_length=50, blank=True, null=True, default='')
    certidao_livro = models.CharField(max_length=50, blank=True, null=True, default='')
    tipo_sanguineo = models.CharField(max_length=3, default='')
    rua = models.CharField(max_length=100, default='')
    numero = models.CharField(max_length=10, default='')
    cep = models.CharField(max_length=10, default='')
    bairro = models.CharField(max_length=50, default='')
    cidade = models.CharField(max_length=50, default='')
    estado = models.CharField(max_length=2, default='')
    email = models.EmailField(default='')
    telefone = models.CharField(max_length=20, default='')
    ativo = models.BooleanField(default=True)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, null=True, blank=True)
    data_ingresso = models.DateField(null=True, blank=True)

    cor_raca = models.CharField(
        max_length=20, null=True, blank=True,
        choices=[
            ('branca','Branca'),
            ('preta','Preta'),
            ('parda','Parda'),
            ('amarela','Amarela'),
            ('indigena','Indígena'),
            ('nao_informado','Não informado'),
        ]
    )

    responsavel_financeiro = models.CharField(
        max_length=10, null=True, blank=True,
        choices=[('pai','Pai'), ('mae','Mãe'), ('outro','Outro')]
    )

    situacao_familiar = models.CharField(
        max_length=12, null=True, blank=True,
        choices=[('casados','Casados'), ('separados','Separados'), ('outros','Outros')]
    )

    dispensa_ensino_religioso = models.BooleanField(default=False)
    forma_acesso = models.CharField(max_length=50, null=True, blank=True)
    situacao_matricula = models.CharField(
        max_length=20, null=True, blank=True,
        choices=[
            ("matricula", "Matrícula"),
            ("rematricula", "Rematrícula"),
            ("transferencia", "Transferência"),
        ]
    )

    bolsa_familia = models.BooleanField(default=False)
    serie_ano = models.CharField(max_length=50, blank=True)
    turno_aluno = models.CharField(max_length=20, blank=True)
    possui_necessidade_especial = models.BooleanField(default=False)

    turma_principal = models.ForeignKey(
        "Turma",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alunos_principais"
    )

    def __str__(self):
        return f"{self.nome} - {self.matricula}"


# ================================================
#  RESPONSÁVEL (agora vários)
# ================================================
class Responsavel(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="responsaveis")
    nome = models.CharField(max_length=255, default='')
    cpf = models.CharField(max_length=14, default='')
    parentesco = models.CharField(max_length=50, default='')
    telefone = models.CharField(max_length=20, default='')
    telefone_secundario = models.CharField(max_length=20, blank=True, null=True, default='')
    email = models.EmailField(default='')

    TIPO_CHOICES = [
        ('pai', 'Pai'),
        ('mae', 'Mãe'),
        ('responsavel', 'Responsável'),
    ]

    tipo = models.CharField(
    max_length=12,
    choices=[
        ('pai','Pai'),
        ('mae','Mãe'),
        ('responsavel','Responsável'),
    ],
    null=True, blank=True
)
    identidade = models.CharField(max_length=30, null=True, blank=True)
    escolaridade = models.CharField(max_length=50, null=True, blank=True)
    profissao = models.CharField(max_length=60, null=True, blank=True)


# ================================================
#  SAÚDE
# ================================================
class Saude(models.Model):
    aluno = models.OneToOneField(Aluno, on_delete=models.CASCADE)
    possui_necessidade_especial = models.BooleanField(default=False)
    descricao_necessidade = models.TextField(blank=True, null=True, default='')
    usa_medicacao = models.BooleanField(default=False)
    quais_medicacoes = models.TextField(blank=True, null=True, default='')
    possui_alergia = models.BooleanField(default=False)
    descricao_alergia = models.TextField(blank=True, null=True, default='')


# ================================================
#  TRANSPORTE
# ================================================
class TransporteEscolar(models.Model):
    aluno = models.OneToOneField(Aluno, on_delete=models.CASCADE)
    usa_transporte_escolar = models.BooleanField(default=False)
    trajeto = models.CharField(max_length=255, blank=True, null=True, default='')
    usa_transporte_publico = models.BooleanField(default=False)


# ================================================
#  AUTORIZAÇÕES
# ================================================
class Autorizacoes(models.Model):
    aluno = models.OneToOneField(Aluno, on_delete=models.CASCADE)
    autorizacao_saida_sozinho = models.BooleanField(default=False)
    autorizacao_fotos_eventos = models.BooleanField(default=False)
    pessoa_autorizada_buscar = models.TextField(blank=True, null=True, default='')
    usa_transporte_publico = models.BooleanField(default=False)


# ================================================
#  TURMA
# ================================================
class Turma(models.Model):
    nome = models.CharField(max_length=100)
    turno = models.CharField(max_length=20)
    ano = models.IntegerField()
    sala = models.CharField(max_length=20)
    descricao = models.TextField(blank=True)

    alunos = models.ManyToManyField(
        Aluno,
        blank=True,
        related_name='turmas'
    )

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.nome} - {self.turno}"


# ================================================
#  TURMA + DISCIPLINA + PROFESSOR
# ================================================
class TurmaDisciplina(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    professor = models.ForeignKey(
        Docente,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, null=True)

    class Meta:
        unique_together = ('turma', 'disciplina', 'professor')

    def save(self, *args, **kwargs):
        if not self.escola and self.professor:
            self.escola = self.professor.escola
        super().save(*args, **kwargs)


# ================================================
#  CHAMADA + PRESENÇA
# ================================================
class Chamada(models.Model):
    data = models.DateField()
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    professor = models.ForeignKey(Docente, null=True, blank=True, on_delete=models.SET_NULL)
    feita_por = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["data", "turma", "disciplina"],
                name="unique_chamada_por_dia"
            )
        ]

class Presenca(models.Model):
    chamada = models.ForeignKey(Chamada, on_delete=models.CASCADE)
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    presente = models.BooleanField(default=True)
    observacao = models.TextField(blank=True)

    class Meta:
        unique_together = ('chamada', 'aluno')

    def __str__(self):
        return f"{self.aluno.nome} - {self.chamada.data} - {'Presente' if self.presente else 'Ausente'}"


class Nota(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)

    bimestre = models.PositiveSmallIntegerField(
        choices=[(1,'1º'),(2,'2º'),(3,'3º'),(4,'4º')],
        null=True,
        blank=True
    )

    valor = models.DecimalField(max_digits=5, decimal_places=2, default=0)

   
class NomeTurma(models.Model):
    nome = models.CharField(max_length=100)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome
    

#===================================================================
# Registro Pedagogico
#===================================================================

class RegistroPedagogico(models.Model):
    TRIMESTRES = (
        (1, "I Trimestre"),
        (2, "II Trimestre"),
        (3, "III Trimestre"),
        (4, "IV Trimestre"),
    )

    aluno = models.ForeignKey(
        "Aluno",
        on_delete=models.CASCADE,
        related_name="registros_pedagogicos",
        verbose_name="Aluno",
    )

    turma = models.ForeignKey(
        "Turma",
        on_delete=models.CASCADE,
        related_name="registros_pedagogicos",
        verbose_name="Turma",
    )

    ano_letivo = models.PositiveIntegerField(
        verbose_name="Ano Letivo"
    )

    trimestre = models.PositiveSmallIntegerField(
        choices=TRIMESTRES,
        verbose_name="Trimestre",
    )

    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações Pedagógicas",
        help_text="Registro descritivo do desenvolvimento do aluno no trimestre",
    )

    escola = models.ForeignKey(
        "Escola",
        on_delete=models.CASCADE,
        related_name="registros_pedagogicos",
        verbose_name="Escola",
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em",
    )

    class Meta:
        verbose_name = "Registro Pedagógico"
        verbose_name_plural = "Registros Pedagógicos"
        ordering = ["aluno", "ano_letivo", "trimestre"]
        constraints = [
            models.UniqueConstraint(
                fields=["aluno", "turma", "ano_letivo", "trimestre"],
                name="unique_registro_pedagogico_trimestre",
            )
        ]

    def __str__(self):
        return (
            f"{self.aluno} - {self.get_trimestre_display()} "
            f"({self.ano_letivo})"
        )
