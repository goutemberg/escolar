from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import uuid
from home.utils_core import gerar_matricula_unica
import random
import string


def gerar_codigo_cliente():
    caracteres = string.ascii_uppercase + string.digits
    return 'ESC-' + ''.join(random.choices(caracteres, k=6))


# ================================================
#  ESCOLA
# ================================================
class Escola(models.Model):

    TEMA_CHOICES = [
        ("legacy", "Escola Pequeno Aprendiz"),
        ("nucleo", "Padrão Núcleo Escolar"),
    ]

    codigo_cliente = models.CharField(
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        editable=False
    )

    nome = models.CharField(max_length=255, unique=True)

    cnpj = models.CharField(
        max_length=18,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{14}$',
                message='CNPJ inválido'
            )
        ]
    )

    telefone = models.CharField(
        max_length=16,
        validators=[
            RegexValidator(
                regex=r'^\(?\d{2}\)?[\s-]?\d{4,5}-?\d{4}$',
                message='Telefone inválido'
            )
        ]
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

    tema = models.CharField(
        max_length=20,
        choices=TEMA_CHOICES,
        default="nucleo",
    )
    financeiro_ativo = models.BooleanField(
        default=False,
        verbose_name="Módulo financeiro ativo"
    )

    def clean(self):
        if self.cnpj:
            self.cnpj = self.cnpj.replace('.', '').replace('/', '').replace('-', '')

        if Escola.objects.filter(cnpj=self.cnpj).exclude(id=self.id).exists():
            raise ValidationError("Este CNPJ já está cadastrado no sistema.")

    def save(self, *args, **kwargs):
        if not self.codigo_cliente:
            while True:
                codigo = gerar_codigo_cliente()
                if not Escola.objects.filter(codigo_cliente=codigo).exists():
                    self.codigo_cliente = codigo
                    break

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.codigo_cliente})"


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
        ('financeiro', 'Financeiro'),
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
    roles = models.ManyToManyField('Role', blank=True)

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


class Role(models.Model):
    nome = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nome


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
    dia_vencimento = models.IntegerField(null=True, blank=True)

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

    desconto_mensal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Desconto automático aplicado nas mensalidades do aluno"
    )

    turma_principal = models.ForeignKey(
        "Turma",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alunos_principais"
    )

    # =========================================================
    # 🔥 VALIDAÇÃO E CONSISTÊNCIA
    # =========================================================

    def save(self, *args, **kwargs):

        # 🔥 REGRA 1: aluno precisa ter turma
        if not self.turma_principal:

            # tenta recuperar da relação M2M
            turma = self.turmas.first()

            if turma:
                self.turma_principal = turma
            else:
                raise ValidationError("Aluno precisa ter uma turma principal.")

        super().save(*args, **kwargs)

        # 🔥 REGRA 2: garantir que turma_principal esteja no M2M
        if self.turma_principal and not self.turmas.filter(id=self.turma_principal.id).exists():
            self.turmas.add(self.turma_principal)

        # 🔥 REGRA 3: garantir apenas UMA turma ativa
        turmas_ids = list(self.turmas.values_list('id', flat=True))

        if len(turmas_ids) > 1:
            self.turmas.clear()
            self.turmas.add(self.turma_principal)

    def __str__(self):
        return f"{self.nome} ({self.matricula})"

    @property
    def turma(self):

        if self.turma_principal:
            return self.turma_principal

        if hasattr(self, "turmas") and self.turmas.exists():
            return self.turmas.first()

        return None

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
    AVALIACAO_CHOICES = [
        ("NUM", "Numérica (nota)"),
        ("CON", "Conceito (E/O/B)"),
    ]

    STATUS_CHOICES = [
        ("ATIVA", "Ativa"),
        ("INATIVA", "Inativa"),
    ]

    TIPO_TURMA_CHOICES = [
        ("INF", "Infantil"),
        ("FUN", "Fundamental"),
        ("MED", "Médio"),
    ]

    nome = models.CharField(max_length=100)
    turno = models.CharField(max_length=20)
    ano = models.IntegerField()  

    sala = models.CharField(max_length=20)
    descricao = models.TextField(blank=True)

    
    ano_letivo = models.ForeignKey(
        'AnoLetivo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turmas'
    )

    sistema_avaliacao = models.CharField(
        max_length=3,
        choices=AVALIACAO_CHOICES,
        default="NUM",
    )

    tipo_turma = models.CharField(
        max_length=3,
        choices=TIPO_TURMA_CHOICES,
        default="FUN",
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="ATIVA",
    )

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
        if self.ano_letivo:
            return f"{self.nome} - {self.turno} ({self.ano}) [{self.ano_letivo.ano}]"
        return f"{self.nome} - {self.turno} ({self.ano})"


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
#  DIÁRIO DE CLASSE
# ================================================
class DiarioDeClasse(models.Model):

    STATUS_AULA = [
        ('PLANEJADA', 'Planejada'),
        ('REALIZADA', 'Realizada'),
        ('CANCELADA', 'Cancelada'),
        ('INVALIDA', 'Inválida'),
    ]

    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        related_name="diarios"
    )

    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        related_name="diarios"
    )

    professor = models.ForeignKey(
        Docente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="diarios"
    )

    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="diarios_criados"
    )

    data_ministrada = models.DateField()
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)

    resumo_conteudo = models.TextField()

    # ✅ NOVO CAMPO (ETAPA 1 – SEGURO)
    status = models.CharField(
        max_length=10,
        choices=STATUS_AULA,
        default='REALIZADA'
    )

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name="diarios_classe"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Diário de Classe"
        verbose_name_plural = "Diários de Classe"
        ordering = ["-data_ministrada", "-criado_em"]

    def __str__(self):
        return f"{self.turma} - {self.data_ministrada}"


# ================================================
#  CHAMADA (REGISTRO DE PRESENÇA DA AULA)
# ================================================
class Chamada(models.Model):

    diario = models.OneToOneField(
        "DiarioDeClasse",
        on_delete=models.CASCADE,
        related_name="chamada"
    )

    criado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chamadas_criadas"
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chamada"
        verbose_name_plural = "Chamadas"

    def __str__(self):
        return f"Chamada - {self.diario}"



class Presenca(models.Model):
    STATUS_CHOICES = (
        ("P", "Presente"),
        ("F", "Falta"),
        ("J", "Falta Justificada"),
    )

    chamada = models.ForeignKey(Chamada, on_delete=models.CASCADE, related_name="presencas")
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="presencas")

    # ✅ novo: status real
    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        default="P",
        db_index=True,
        verbose_name="Status",
    )

    # ✅ mantém por compat (PDF antigo, relatórios, etc.)
    # regra: presente = True somente quando status == "P"
    presente = models.BooleanField(default=True)

    observacao = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["chamada", "aluno"],
                name="unique_presenca_chamada_aluno",
            )
        ]

    def save(self, *args, **kwargs):
        # ✅ garante consistência: presente sempre acompanha o status
        self.presente = (self.status == "P")
        super().save(*args, **kwargs)

    def __str__(self):
        # tenta pegar data do diário (se existir) sem quebrar
        data_str = "-"
        try:
            if hasattr(self.chamada, "diario") and self.chamada.diario and getattr(self.chamada.diario, "data_ministrada", None):
                data_str = self.chamada.diario.data_ministrada.strftime("%d/%m/%Y")
        except Exception:
            pass

        return f"{self.aluno.nome} - {data_str} - {self.get_status_display()}"

   
class NomeTurma(models.Model):
    nome = models.CharField(max_length=100)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome
    

# ===================================================================
# Relatório Individual
# ===================================================================

class RelatorioIndividual(models.Model):
    BIMESTRES = (
        (1, "I Bimestre"),
        (2, "II Bimestre"),
        (3, "III Bimestre"),
        (4, "IV Bimestre"),
    )

    aluno = models.ForeignKey(
        "Aluno",
        on_delete=models.CASCADE,
        related_name="relatorios_individuais",
        verbose_name="Aluno",
    )

    turma = models.ForeignKey(
        "Turma",
        on_delete=models.CASCADE,
        related_name="relatorios_individuais",
        verbose_name="Turma",
    )

    ano_letivo = models.PositiveIntegerField(
        verbose_name="Ano Letivo"
    )

    bimestre = models.PositiveSmallIntegerField(
        choices=BIMESTRES,
        verbose_name="Bimestre",
    )

    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações Pedagógicas",
        help_text="Registro descritivo do desenvolvimento do aluno no bimestre",
    )

    escola = models.ForeignKey(
        "Escola",
        on_delete=models.CASCADE,
        related_name="relatorios_individuais",
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
        verbose_name = "Relatório Individual"
        verbose_name_plural = "Relatórios Individuais"
        ordering = ["aluno", "ano_letivo", "bimestre"]
        constraints = [
            models.UniqueConstraint(
                fields=["aluno", "turma", "ano_letivo", "bimestre"],
                name="unique_relatorio_individual_bimestre",
            )
        ]

    def __str__(self):
        return f"{self.aluno} - {self.get_bimestre_display()} ({self.ano_letivo})"

    def __str__(self):
        return (
            f"{self.aluno} - {self.get_trimestre_display()} "
            f"({self.ano_letivo})"
        )

# ===================================================================
# Registro Pedagógico
# ===================================================================

class RegistroPedagogico(models.Model):
    BIMESTRES = (
        (1, "I Bimestre"),
        (2, "II Bimestre"),
        (3, "III Bimestre"),
        (4, "IV Bimestre"),
    )

    turma = models.ForeignKey(
        "Turma",
        on_delete=models.CASCADE,
        related_name="registros_pedagogicos",
        verbose_name="Turma",
    )

    disciplina = models.ForeignKey(
        "Disciplina",
        on_delete=models.CASCADE,
        related_name="registros_pedagogicos",
        verbose_name="Disciplina",
    )

    ano_letivo = models.PositiveIntegerField(
        verbose_name="Ano Letivo"
    )

    bimestre = models.PositiveSmallIntegerField(
        choices=BIMESTRES,
        verbose_name="Bimestre",
    )

    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações Pedagógicas",
        help_text="Registro pedagógico da turma por disciplina no bimestre",
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
        ordering = ["turma", "disciplina", "ano_letivo", "bimestre"]
        constraints = [
            models.UniqueConstraint(
                fields=["turma", "disciplina", "ano_letivo", "bimestre"],
                name="unique_registro_pedagogico_bimestre",
            )
        ]

    def __str__(self):
        return f"{self.turma} - {self.disciplina} - {self.get_bimestre_display()} ({self.ano_letivo})"

###########################################################################
# notas
###########################################################################

class TipoAvaliacao(models.Model):
    nome = models.CharField(max_length=100)
    peso = models.DecimalField(max_digits=5, decimal_places=2, default=1)

    escola = models.ForeignKey(
        'Escola',
        on_delete=models.CASCADE,
        related_name='tipos_avaliacao'
    )

    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nome} ({self.escola.nome})"


class Avaliacao(models.Model):

    BIMESTRES = [
        (1, '1º Bimestre'),
        (2, '2º Bimestre'),
        (3, '3º Bimestre'),
        (4, '4º Bimestre'),
    ]

    turma = models.ForeignKey(
        'Turma',
        on_delete=models.CASCADE,
        related_name='avaliacoes',
        null=True,
        blank=True,
    )

    disciplina = models.ForeignKey(
        'Disciplina',
        on_delete=models.CASCADE,
        related_name='avaliacoes'
    )

    tipo = models.ForeignKey(
        'TipoAvaliacao',
        on_delete=models.PROTECT,
        related_name='avaliacoes'
    )

    descricao = models.CharField(max_length=200)

    bimestre = models.IntegerField(
        choices=BIMESTRES
    )

    data = models.DateField()

    escola = models.ForeignKey(
        'Escola',
        on_delete=models.CASCADE,
        related_name='avaliacoes'
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.descricao} - {self.disciplina.nome} - {self.turma.nome}"

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'turma',
                    'disciplina',
                    'bimestre',
                    'descricao',
                    'escola'
                ],
                name='unique_avaliacao_por_turma_disciplina_bimestre_escola'
            )
        ]

        indexes = [
            models.Index(fields=['turma', 'disciplina']),
            models.Index(fields=['disciplina', 'bimestre']),
            models.Index(fields=['escola', 'bimestre']),
        ]

        ordering = ['bimestre', 'data']


class Nota(models.Model):

    CONCEITO_CHOICES = [
        ("E", "Evolução"),
        ("O", "Ótimo"),
        ("B", "Bom"),
    ]

    aluno = models.ForeignKey(
        'Aluno',
        on_delete=models.CASCADE,
        related_name='notas'
    )

    avaliacao = models.ForeignKey(
        'Avaliacao',
        on_delete=models.CASCADE,
        related_name='notas'
    )

    # ✅ nota normal
    valor = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # ✅ conceito
    conceito = models.CharField(
        max_length=1,
        choices=CONCEITO_CHOICES,
        null=True,
        blank=True
    )

    # ✅ NOVO: recuperação do bimestre (opcional)
    recuperacao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    escola = models.ForeignKey(
        'Escola',
        on_delete=models.CASCADE,
        related_name='notas'
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('aluno', 'avaliacao')

    def clean(self):

        if self.valor is not None and self.conceito:
            raise ValidationError("Preencha apenas valor OU conceito.")

        if self.valor is None and not self.conceito:
            raise ValidationError("Informe um valor (nota) ou um conceito.")

    def save(self, *args, **kwargs):

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):

        if self.conceito:
            return f"{self.aluno.nome} - {self.avaliacao.descricao} - {self.get_conceito_display()}"

        return f"{self.aluno.nome} - {self.avaliacao.descricao} - {self.valor}"
    

class ModeloAvaliacao(models.Model):

    escola = models.ForeignKey('Escola', on_delete=models.CASCADE)

    disciplina = models.ForeignKey('Disciplina', on_delete=models.CASCADE)

    tipo = models.ForeignKey(
        'TipoAvaliacao',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    nome = models.CharField(max_length=100)

    peso = models.DecimalField(max_digits=4, decimal_places=2, default=1)

    quantidade = models.IntegerField(default=1)  

    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)


from django.utils import timezone
from datetime import timedelta

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.criado_em + timedelta(minutes=15)

    def __str__(self):
        return f"{self.user.username} - {self.token}"


# home/models.py

class LoginLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    cpf = models.CharField(max_length=20, null=True, blank=True)
    ip = models.GenericIPAddressField()
    sucesso = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cpf} - {'OK' if self.sucesso else 'FAIL'}"
    

class UserEscola(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    escola = models.ForeignKey('Escola', on_delete=models.CASCADE)
    roles = models.ManyToManyField('Role', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'escola')

    def __str__(self):
        return f"{self.user} - {self.escola}"


class AvisoPublico(models.Model):
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo



class AvaliacaoCategoria(models.Model):
    nome = models.CharField(max_length=100)
    escola = models.ForeignKey('Escola', on_delete=models.CASCADE)
    ordem = models.IntegerField(default=0)

    def __str__(self):
        return self.nome


class AvaliacaoItem(models.Model):
    escola = models.ForeignKey('Escola', on_delete=models.CASCADE)

    categoria = models.ForeignKey(
        AvaliacaoCategoria,
        on_delete=models.CASCADE,
        related_name="itens"  # 🔥 AQUI
    )

    descricao = models.CharField(max_length=255)
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.descricao


class AvaliacaoInfantil(models.Model):
    aluno = models.ForeignKey('Aluno', on_delete=models.CASCADE)
    turma = models.ForeignKey('Turma', on_delete=models.CASCADE)

    bimestre = models.IntegerField()
    ano = models.IntegerField()

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('aluno', 'turma', 'bimestre', 'ano')


class AvaliacaoResposta(models.Model):
    OPCOES = [
        ('O', 'Ótimo'),
        ('B', 'Bom'),
        ('E', 'Em evolução'),
    ]

    avaliacao = models.ForeignKey(AvaliacaoInfantil, on_delete=models.CASCADE)
    item = models.ForeignKey(AvaliacaoItem, on_delete=models.CASCADE)
    valor = models.CharField(max_length=1, choices=OPCOES)

    class Meta:
        unique_together = ('avaliacao', 'item')


class ObservacaoInfantil(models.Model):
    aluno = models.ForeignKey("Aluno", on_delete=models.CASCADE)
    turma = models.ForeignKey("Turma", on_delete=models.CASCADE)
    bimestre = models.IntegerField()
    ano = models.IntegerField()

    texto = models.TextField(blank=True, default="")

    escola = models.ForeignKey("Escola", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("aluno", "turma", "bimestre", "ano")

    def __str__(self):
        return f"{self.aluno.nome} - {self.bimestre}/{self.ano}"



class AnoLetivo(models.Model):
    ano = models.IntegerField(unique=True)
    ativo = models.BooleanField(default=True)
    encerrado = models.BooleanField(default=False)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)

    def __str__(self):
        return str(self.ano)
    

class Boletim(models.Model):

    aluno = models.ForeignKey("Aluno", on_delete=models.CASCADE)
    turma = models.ForeignKey("Turma", on_delete=models.CASCADE)

    dados = models.JSONField()  # 🔥 snapshot completo do boletim

    pdf = models.FileField(upload_to="boletins/", null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("aluno", "turma")

    def __str__(self):
        return f"{self.aluno.nome} - {self.turma.nome}"
