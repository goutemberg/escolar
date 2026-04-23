# ============================================
# 📌 IMPORTS ORGANIZADOS E SEM DUPLICAÇÕES
# ============================================

# ---- Standard Library ----
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from django.contrib.auth import login, authenticate
from home.utils import validar_senha_forte, get_client_ip, arredondar_media_personalizada
from home.models import User, LoginLog, UserEscola


# ---- Django Core ----
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction, models
from django.db.models import Prefetch, Q, IntegerField
from django.db.models.functions import Cast, Substr
from django.db.utils import DataError, IntegrityError
from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from collections import defaultdict

# ---- Third-Party ----
import pandas as pd
from babel.dates import format_date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---- Local Apps ----
from .forms import EscolaForm

from .models import (
    Escola,
    Docente,
    Aluno,
    Responsavel,
    Saude,
    TransporteEscolar,
    Autorizacoes,
    Turma,
    Disciplina,
    Funcionario,
    TurmaDisciplina,
    Presenca,
    Chamada,
    Nota,
    RegistroPedagogico,
    ModeloAvaliacao,
    TipoAvaliacao,
    PasswordResetToken,
    AvisoPublico,
    
)

from home.models import NomeTurma, Avaliacao
from home.decorators import role_required
from home.utils import gerar_matricula_unica
from home.utils_user import criar_usuario_com_cpf

from core.themes import get_base_template



MESES_PT = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
]

def _buscar_pai_mae(aluno):
    """
    Retorna (pai, mae) a partir dos registros de Responsavel do aluno.
    Regras:
      - Primeiro tenta por marcadores explícitos em tipo OU parentesco (casefold),
        incluindo variações com/sem acento.
      - Garante que pai e mãe não sejam o MESMO registro.
      - Se não houver marcador para 'mãe', usa um segundo registro distinto como fallback.
    """
    qs = Responsavel.objects.filter(aluno=aluno).order_by('id')

    pai = qs.filter(
        Q(tipo__iexact='pai') | Q(parentesco__iexact='pai')
    ).first()

    mae = qs.filter(
        Q(tipo__iexact='mae') | Q(tipo__iexact='mãe') |
        Q(parentesco__iexact='mae') | Q(parentesco__iexact='mãe')
    ).first()

    # Evita colisão (pai==mae)
    if pai and mae and pai.pk == mae.pk:
        mae = qs.exclude(pk=pai.pk).filter(
            Q(tipo__iexact='mae') | Q(tipo__iexact='mãe') |
            Q(parentesco__iexact='mae') | Q(parentesco__iexact='mãe')
        ).first()

    # Fallback: se ainda não achou mãe mas existe outro responsável, pega um distinto do pai
    if not mae:
        mae = qs.exclude(pk=getattr(pai, 'pk', None)).first()

    return pai, mae



User = get_user_model()


def index(request):
    if request.user.is_authenticated:
        return render(request, 'pages/index.html')  # sistema

    aviso = AvisoPublico.objects.filter(ativo=True).order_by('-criado_em').first()
    total_escolas = Escola.objects.count()

    return render(request, 'pages/public.html', {
        'aviso': aviso,
        'total_escolas': total_escolas
    })
    

@login_required
def cadastro_escola(request):
    escola = getattr(request.user, 'escola', None)
    return render(request, 'pages/cadastrar_escola.html', {
        'escola': escola
    })


@login_required
def cadastrar_escola_banco(request):
    return JsonResponse({
        'success': False,
        'error': 'Cadastro de escola disponível apenas pelo Django Admin.'
    }, status=403)

@login_required
@role_required(['diretor', 'coordenador'])
def cadastro_aluno(request):
    cadastro_aluno = Escola.objects.all()
    turmas = Turma.objects.filter(escola=request.escola
).order_by('nome')
    niveis_modalidades = ['Infantil', 'Fundamental I', 'Fundamental II']

    context = {
        'cadastro_aluno': cadastro_aluno,
        'turmas': turmas,
        'niveis_modalidades': niveis_modalidades,
    }
    return render(request, 'pages/registrar_aluno.html', context)

@login_required
@role_required(['diretor', 'coordenador'])
def cadastro_funcionarios(request):
    cadastro_funcionario = Escola.objects.all()  
    context = {
        'cadastro_funcionario': cadastro_funcionario 
    }
    return render(request, 'pages/registrar_funcionarios.html', context)


@login_required
@role_required(['diretor', 'coordenador'])
def cadastro_professor(request):
    escolas = Escola.objects.all()
    disciplinas = Disciplina.objects.filter(escola=request.escola
)
    context = {
        'cadastro_professor': escolas,
        'disciplinas': disciplinas,
    }
    return render(request, 'pages/registrar_professor.html', context)

@csrf_exempt
@require_POST
def buscar_cnpj(request):
    body = json.loads(request.body)
    cnpj = body.get('cnpj')

    if not validar_cnpj(cnpj):
        return JsonResponse({"error": "CNPJ inválido"}, status=400)

    try:
        escola = Escola.objects.get(cnpj=cnpj, escola=request.escola
)
        return JsonResponse({"exists": True, "escola": {
            "schoolName": escola.nome,
            "schoolPhone": escola.telefone,
            "schoolEmail": escola.email,
            "schoolStreet": escola.endereco,
            "schoolNumber": escola.numero,
            "schoolComplement": escola.complemento,
            "schoolNeighborhood": escola.bairro,
            "schoolCity": escola.cidade,
            "schoolState": escola.estado,
            "schoolWebsite": escola.site,
        }})
    except Escola.DoesNotExist:
        return JsonResponse({"exists": False})

def validar_cnpj(cnpj):
    cnpj = re.sub(r'\D', '', cnpj)
    if len(cnpj) != 14 or cnpj in [s * 14 for s in "0123456789"]:
        return False
    def calc_digito(cnpj, peso):
        soma = sum(int(cnpj[i]) * peso[i] for i in range(len(peso)))
        resto = soma % 11
        return '0' if resto < 2 else str(11 - resto)
    peso1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    peso2 = [6] + peso1
    dig1 = calc_digito(cnpj[:12], peso1)
    dig2 = calc_digito(cnpj[:12] + dig1, peso2)
    return cnpj[-2:] == dig1 + dig2


@csrf_exempt
@login_required
@role_required(['diretor', 'coordenador'])
@transaction.atomic
def cadastrar_professor_banco(request):

    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'Método não permitido'},
            status=405
        )

    try:
        data = json.loads(request.body)

        professor_id = data.get('id')

        cpf = ''.join(filter(str.isdigit, data.get('doctorCpf', '')))
        nome = data.get('doctorName', '').strip()
        nascimento = parse_date(data.get('birthdate'))
        email = data.get('email', '').strip()
        telefone = data.get('phone', '').strip()
        telefone_secundario = data.get('phone2', '').strip()
        cep = data.get('cep', '').strip()
        endereco = data.get('address', '').strip()
        numero = data.get('number', '').strip()
        complemento = data.get('complement', '').strip()
        bairro = data.get('bairro', '').strip()
        cidade = data.get('city', '').strip()
        estado = data.get('state', '').strip()
        cargo = data.get('cargo', '').strip()
        grau_instrucao = data.get('grau_instrucao', '').strip()
        formacao = data.get('formacao', '').strip()
        experiencia = data.get('experiencia', '').strip()
        sexo = data.get('sexo', '').strip()
        ativo = str(data.get('ativo', 'True')).lower() == 'true'
        senha = data.get('senha')

        escola = request.escola  # 🔥 NOVO

        if not escola:
            return JsonResponse(
                {'success': False, 'error': 'Usuário não vinculado a escola.'},
                status=403
            )

        if not cpf or not nome:
            return JsonResponse(
                {'success': False, 'error': 'CPF e nome são obrigatórios.'},
                status=400
            )

        # ========================= EDIÇÃO =========================
        if professor_id:

            professor = get_object_or_404(
                Docente,
                id=professor_id,
                escola=escola
            )

            professor.nome = nome
            professor.email = email
            professor.telefone = telefone
            professor.telefone_secundario = telefone_secundario
            professor.nascimento = nascimento
            professor.cargo = cargo
            professor.grau_instrucao = grau_instrucao
            professor.formacao = formacao
            professor.experiencia = experiencia
            professor.sexo = sexo
            professor.ativo = ativo

            professor.cep = cep
            professor.endereco = endereco
            professor.numero = numero
            professor.complemento = complemento
            professor.bairro = bairro
            professor.cidade = cidade
            professor.estado = estado

            professor.save()

            if professor.user:
                professor.user.is_active = ativo
                professor.user.save(update_fields=["is_active"])

            return JsonResponse({'success': True})

        # ========================= CREATE =========================

        if not senha:
            return JsonResponse(
                {'success': False, 'error': 'Senha temporária ausente.'},
                status=400
            )

        # 🔥 1️⃣ BUSCA OU CRIA USUÁRIO GLOBAL
        partes = nome.split()
        first = partes[0]
        last = ' '.join(partes[1:]) if len(partes) > 1 else ''

        usuario, created = User.objects.get_or_create(
            cpf=cpf,
            defaults={
                "username": cpf,
                "email": email,
                "first_name": first,
                "last_name": last,
                "role": cargo,
                "is_active": ativo,
                "senha_temporaria": True
            }
        )

        # 🔥 se criou agora → define senha
        if created:
            usuario.set_password(senha)
            usuario.save()

        # 🔥 2️⃣ VINCULA À ESCOLA (MULTI-ESCOLA)
        UserEscola.objects.get_or_create(
            user=usuario,
            escola=escola
        )

        # DOCENTE (POR ESCOLA)
        docente, created_docente = Docente.objects.get_or_create(
            cpf=cpf,
            escola=escola,
            defaults={
                "user": usuario,
                "escola": escola,
                "nome": nome,
                "nascimento": nascimento,
                "email": email,
                "telefone": telefone,
                "telefone_secundario": telefone_secundario,
                "cep": cep,
                "endereco": endereco,
                "numero": numero,
                "complemento": complemento,
                "bairro": bairro,
                "cidade": cidade,
                "estado": estado,
                "cargo": cargo,
                "grau_instrucao": grau_instrucao,
                "formacao": formacao,
                "experiencia": experiencia,
                "sexo": sexo,
                "ativo": ativo,
            }
        )

        if not created_docente:
            docente.user = usuario
            docente.nome = nome
            docente.nascimento = nascimento
            docente.email = email
            docente.telefone = telefone
            docente.telefone_secundario = telefone_secundario
            docente.cep = cep
            docente.endereco = endereco
            docente.numero = numero
            docente.complemento = complemento
            docente.bairro = bairro
            docente.cidade = cidade
            docente.estado = estado
            docente.cargo = cargo
            docente.grau_instrucao = grau_instrucao
            docente.formacao = formacao
            docente.experiencia = experiencia
            docente.sexo = sexo
            docente.ativo = ativo
            docente.save()

        return JsonResponse({
            'success': True,
            'senha': senha if created else None,
            'message': 'Professor vinculado com sucesso' if not created else None
        })

    except IntegrityError:
        transaction.set_rollback(True)
        return JsonResponse(
            {'success': False, 'error': 'Erro de integridade ao salvar professor.'},
            status=400
        )

    except Exception as e:
        transaction.set_rollback(True)
        return JsonResponse(
            {'success': False, 'error': f'Erro interno: {str(e)}'},
            status=500
        )
    

@login_required
@role_required(['diretor', 'coordenador'])
def listar_professores(request):
    professores = (
        Docente.objects
        .select_related('user')
        .filter(escola=request.escola
)
        .order_by('nome')
    )

    professores_json = []
    for p in professores:
        professores_json.append({
            "id": p.id,
            "nome": p.nome,
            "cpf": p.cpf,
            "cargo": p.cargo,
            "telefone": p.telefone,
            "telefone_secundario": p.telefone_secundario,
            "email": p.email,
            "sexo": p.sexo,
            "ativo": p.ativo,
        })

    return render(request, 'pages/listar_professores.html', {
        "professores_json": json.dumps(professores_json, ensure_ascii=False),
    })

# =========================
# Ativar Inativar Professor
# =========================

@login_required
@role_required(['diretor', 'coordenador'])
def toggle_status_professor(request, id):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    professor = get_object_or_404(
        Docente,
        id=id,
        escola=request.escola

    )

    professor.ativo = not professor.ativo
    professor.save(update_fields=["ativo"])

    # controla login
    if professor.user:
        professor.user.is_active = professor.ativo
        professor.user.save(update_fields=["is_active"])

    return JsonResponse({
        "success": True,
        "ativo": professor.ativo
    })

@login_required
@role_required(['diretor', 'coordenador'])
def form_professor(request, professor_id=None):
    return render(request, 'pages/registrar_professor.html', {
        'professor_id': professor_id
    })


# =========================
# Editar professor 
# =========================
@login_required
@role_required(['diretor', 'coordenador'])
def api_professor_detalhe(request, professor_id):
    p = get_object_or_404(
        Docente,
        id=professor_id,
        escola=request.escola

    )

    return JsonResponse({
        "id": p.id,
        "nome": p.nome,
        "cpf": p.cpf,
        "nascimento": p.nascimento,
        "email": p.email,
        "telefone": p.telefone,
        "telefone_secundario": getattr(p, 'telefone_secundario', ''),
        "cep": p.cep,
        "endereco": p.endereco,
        "numero": p.numero,
        "complemento": p.complemento,
        "bairro": p.bairro,
        "cidade": p.cidade,
        "estado": p.estado,
        "cargo": p.cargo,
        "grau_instrucao": p.grau_instrucao,
        "formacao": p.formacao,
        "experiencia": p.experiencia,
        "sexo": p.sexo,
    })


@csrf_exempt
@login_required
@role_required(['diretor', 'coordenador'])
def editar_professor(request, prof_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            professor = Docente.objects.get(id=prof_id, escola=request.escola
)

            professor.nome = data.get('nome', professor.nome)
            professor.email = data.get('email', professor.email)
            professor.telefone = data.get('telefone', professor.telefone)
            professor.nascimento = data.get('data_nascimento') or None
            professor.sexo = data.get('sexo', professor.sexo)
            professor.endereco = data.get('endereco', professor.endereco)
            professor.formacao = data.get('formacao', professor.formacao)

            ids_disciplinas = data.get('disciplinas', [])
            professor.save()
            professor.disciplinas.set(ids_disciplinas)

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        

@csrf_exempt
@login_required
def alternar_status_professor(request, prof_id):
    if request.method == 'POST':
        try:
            professor = Docente.objects.get(
                id=prof_id,
                escola=request.escola

            )

            # alterna status
            professor.ativo = not professor.ativo
            professor.save()

            # controla acesso ao sistema
            if professor.user:
                professor.user.is_active = professor.ativo
                professor.user.save(update_fields=["is_active"])

            return JsonResponse({
                'success': True,
                'novo_status': professor.ativo
            })

        except Docente.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Professor não encontrado ou sem permissão'
            }, status=404)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': 'Método inválido'
    }, status=405)


@csrf_exempt
def to_bool(value):
    return str(value).lower() in ['true', '1', 'sim']


def safe_bool(v, default=False):
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in ('true','1','on','yes','y','sim'):
        return True
    if s in ('false','0','off','no','n','nao','não'):
        return False
    return default

def omit_none(dct):
    return {k: v for k, v in dct.items() if v is not None}

def to_bool(v):
    if isinstance(v, bool): return v
    return str(v).strip().lower() in ("1","true","t","sim","yes","y")


@csrf_exempt
@login_required
def salvar_aluno(request):
    if request.method != "POST":
        return JsonResponse({'mensagem': 'Método não permitido'}, status=405)

    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    obrig = ['nome', 'data_nascimento', 'rua', 'numero', 'bairro', 'cidade', 'estado']
    for c in obrig:
        if not data.get(c):
            return JsonResponse(
                {'status': 'erro', 'mensagem': f'O campo "{c}" é obrigatório.'},
                status=400
            )

    aluno_id = data.get('aluno_id')

    try:
        with transaction.atomic():

            dn = datetime.strptime(data.get('data_nascimento'), "%Y-%m-%d").date()

            data_ingresso = None
            if data.get('data_ingresso'):
                data_ingresso = datetime.strptime(
                    data.get('data_ingresso'), "%Y-%m-%d"
                ).date()

            # ==========================================================
            # EDIÇÃO
            # ==========================================================
            if aluno_id:
                aluno = (
                    Aluno.objects
                    .select_for_update()
                    .get(id=aluno_id, escola=request.escola
)
                )

                aluno.nome = data.get('nome', '')
                aluno.data_nascimento = dn
                aluno.cpf = data.get('cpf', '')
                aluno.rg = data.get('rg', '')
                aluno.sexo = data.get('sexo', '')
                aluno.nacionalidade = data.get('nacionalidade', '')
                aluno.naturalidade = data.get('naturalidade', '')
                aluno.certidao_numero = data.get('certidao_numero', '')
                aluno.certidao_livro = data.get('certidao_livro', '')
                aluno.tipo_sanguineo = data.get('tipo_sanguineo', '')
                aluno.rua = data.get('rua', '')
                aluno.numero = data.get('numero', '')
                aluno.cep = data.get('cep', '')
                aluno.bairro = data.get('bairro', '')
                aluno.cidade = data.get('cidade', '')
                aluno.estado = data.get('estado', '')
                aluno.email = data.get('email', '')
                aluno.telefone = data.get('telefone', '')
                aluno.data_ingresso = data_ingresso
                aluno.cor_raca = data.get('cor_raca') or None
                aluno.responsavel_financeiro = data.get('responsavel_financeiro') or None
                aluno.situacao_familiar = data.get('situacao_familiar') or None

                if data.get('nivel_modalidade'):
                    aluno.forma_acesso = data.get('nivel_modalidade')

                aluno.dispensa_ensino_religioso = to_bool(
                    data.get('dispensa_ensino_religioso')
                )
                aluno.bolsa_familia = to_bool(data.get('bolsa_familia'))
                aluno.serie_ano = data.get('serie_ano', '')
                aluno.turno_aluno = data.get('turno') or data.get('turno_aluno', '')
                dia_vencimento = data.get('dia_vencimento')
                aluno.dia_vencimento = int(dia_vencimento) if dia_vencimento else None
                aluno.save()

            # ==========================================================
            # CADASTRO
            # ==========================================================
            else:
                aluno = Aluno.objects.create(
                    nome=data.get('nome', ''),
                    data_nascimento=dn,
                    cpf=data.get('cpf', ''),
                    rg=data.get('rg', ''),
                    sexo=data.get('sexo', ''),
                    nacionalidade=data.get('nacionalidade', ''),
                    naturalidade=data.get('naturalidade', ''),
                    certidao_numero=data.get('certidao_numero', ''),
                    certidao_livro=data.get('certidao_livro', ''),
                    tipo_sanguineo=data.get('tipo_sanguineo', ''),
                    rua=data.get('rua', ''),
                    numero=data.get('numero', ''),
                    cep=data.get('cep', ''),
                    bairro=data.get('bairro', ''),
                    cidade=data.get('cidade', ''),
                    estado=data.get('estado', ''),
                    email=data.get('email', ''),
                    telefone=data.get('telefone', ''),
                    escola=request.escola
,
                    data_ingresso=data_ingresso,
                    cor_raca=data.get('cor_raca') or None,
                    responsavel_financeiro=data.get('responsavel_financeiro') or None,
                    situacao_familiar=data.get('situacao_familiar') or None,
                    forma_acesso=data.get('nivel_modalidade'),
                    dispensa_ensino_religioso=to_bool(
                        data.get('dispensa_ensino_religioso')
                    ),
                    situacao_matricula=data.get('situacao_matricula') or None,
                    bolsa_familia=to_bool(data.get('bolsa_familia')),
                    serie_ano=data.get('serie_ano', ''),
                    turno_aluno=data.get('turno') or data.get('turno_aluno', ''),
                    dia_vencimento=int(data.get('dia_vencimento')) if data.get('dia_vencimento') else None,
                )

            # ==========================================================
            # TURMA PRINCIPAL
            # ==========================================================
            turma_id = data.get('turma_id')
            if turma_id:
                turma = Turma.objects.filter(
                    id=turma_id,
                    escola=request.escola

                ).first()

                if turma:
                    aluno.turmas.add(turma)

                    if not aluno.turma_principal:
                        aluno.turma_principal = turma
                        aluno.save(update_fields=['turma_principal'])

            # ==========================================================
            # RESPONSÁVEIS (AJUSTADO – NÃO APAGA DADOS EXISTENTES)
            # ==========================================================
            def salvar_responsavel(tipo):
                nome = (data.get(f"{tipo}_nome") or "").strip()
                qs = Responsavel.objects.filter(aluno=aluno, tipo=tipo)

                if nome:
                    Responsavel.objects.update_or_create(
                        aluno=aluno,
                        tipo=tipo,
                        defaults={
                            'nome': nome,
                            'cpf': data.get(f"{tipo}_cpf", ''),
                            'telefone': data.get(f"{tipo}_telefone", ''),
                            'telefone_secundario': data.get(f"{tipo}_telefone2", ''),
                            'email': data.get(f"{tipo}_email", ''),
                            'parentesco': data.get(f"{tipo}_parentesco", '') if tipo == 'responsavel' else '',
                            'identidade': data.get(f"{tipo}_identidade", ''),
                            'escolaridade': data.get(f"{tipo}_escolaridade", ''),
                            'profissao': data.get(f"{tipo}_profissao", ''),
                        }
                    )
                elif qs.exists():
                    return

            salvar_responsavel('responsavel')
            salvar_responsavel('pai')
            salvar_responsavel('mae')

            # ==========================================================
            # SAÚDE
            # ==========================================================
            Saude.objects.update_or_create(
                aluno=aluno,
                defaults={
                    'possui_necessidade_especial': to_bool(
                        data.get('possui_necessidade_especial')
                    ),
                    'descricao_necessidade': data.get('descricao_necessidade', ''),
                    'usa_medicacao': to_bool(data.get('usa_medicacao')),
                    'quais_medicacoes': data.get('quais_medicacoes', ''),
                    'possui_alergia': to_bool(data.get('possui_alergia')),
                    'descricao_alergia': data.get('descricao_alergia', ''),
                }
            )

            # ==========================================================
            # TRANSPORTE
            # ==========================================================
            TransporteEscolar.objects.update_or_create(
                aluno=aluno,
                defaults={
                    'usa_transporte_escolar': to_bool(
                        data.get('utiliza_transporte')
                        or data.get('usa_transporte_escolar')
                    ),
                    'usa_transporte_publico': to_bool(
                        data.get('usa_transporte_publico')
                    ),
                    'trajeto': data.get('trajeto', ''),
                }
            )

            # ==========================================================
            # AUTORIZAÇÕES
            # ==========================================================
            Autorizacoes.objects.update_or_create(
                aluno=aluno,
                defaults={
                    'autorizacao_saida_sozinho': to_bool(
                        data.get('autorizacao_saida_sozinho')
                    ),
                    'autorizacao_fotos_eventos': to_bool(
                        data.get('autorizacao_fotos_eventos')
                    ),
                    'pessoa_autorizada_buscar': data.get(
                        'pessoa_autorizada_buscar', ''
                    ),
                    'usa_transporte_publico': to_bool(
                        data.get('usa_transporte_publico')
                    ),
                }
            )

        return JsonResponse({
            'status': 'sucesso',
            'aluno_id': aluno.id,
            'matricula': aluno.matricula
        })

    except Exception as e:
        return JsonResponse({
            'status': 'erro',
            'mensagem': 'Erro ao salvar aluno.',
            'detalhe': str(e)
        }, status=400)

          
@login_required
def aluno_pdf(request, aluno_id):
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    escola = getattr(aluno, 'escola', None) or getattr(request.user, 'escola', None)

    # Relacionamentos (ajuste se seus related_names forem diferentes)
    responsaveis = list(getattr(aluno, 'responsavel_set', []).all()) if hasattr(aluno, 'responsavel_set') else []
    saude = getattr(aluno, 'saude', None) if hasattr(aluno, 'saude') else None
    transporte = getattr(aluno, 'transporte', None) if hasattr(aluno, 'transporte') else None
    autorizacoes = getattr(aluno, 'autorizacoes', None) if hasattr(aluno, 'autorizacoes') else None

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=1.7*cm, bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle('TitleCenter', parent=styles['Title'], alignment=1, fontSize=16, spaceAfter=6)
    h3 = ParagraphStyle('H3', parent=styles['Heading3'], spaceBefore=10, spaceAfter=6)
    normal = styles['BodyText']

    story = []

    # Cabeçalho da escola
    escola_nome = getattr(escola, 'nome', 'Escola')
    escola_endereco = getattr(escola, 'endereco', '') or ''
    story.append(Paragraph(escola_nome, title))
    if escola_endereco:
        story.append(Paragraph(escola_endereco, normal))
    story.append(Spacer(1, 6))

    # Seção: Dados do Aluno
    story.append(Paragraph("Dados do Aluno", h3))
    dados_aluno = [
        ["Matrícula", aluno.matricula or ""],
        ["Nome", aluno.nome or ""],
        ["Data de Nascimento", str(aluno.data_nascimento or "")],
        ["CPF", aluno.cpf or ""],
        ["RG", aluno.rg or ""],
        ["Sexo", aluno.sexo or ""],
        ["Nacionalidade", aluno.nacionalidade or ""],
        ["Naturalidade", aluno.naturalidade or ""],
        ["Certidão", f"Nº {aluno.certidao_numero or ''} — Livro {aluno.certidao_livro or ''}"],
        ["Tipo sanguíneo", aluno.tipo_sanguineo or ""],
    ]
    t1 = Table(dados_aluno, colWidths=[5*cm, 10*cm])
    t1.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#dddddd')),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#444444')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fafafa')]),
    ]))
    story.append(t1)

    # Seção: Endereço/Contato
    story.append(Paragraph("Endereço e Contato", h3))
    endereco = f"{aluno.rua or ''}, {aluno.numero or ''} — {aluno.bairro or ''} — {aluno.cidade or ''}/{aluno.estado or ''} — CEP {aluno.cep or ''}"
    dados_contato = [
        ["Endereço", endereco],
        ["Email", aluno.email or ""],
        ["Telefone", aluno.telefone or ""],
    ]
    t2 = Table(dados_contato, colWidths=[5*cm, 10*cm])
    t2.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#dddddd')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#444444')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor('#fafafa')]),
    ]))
    story.append(t2)

    # Seção: Responsáveis (se houver)
    if responsaveis:
        story.append(Paragraph("Responsáveis", h3))
        rows = [["Nome", "CPF", "Parentesco", "Telefone", "Email"]]
        for r in responsaveis:
            rows.append([
                getattr(r, 'nome', '') or '',
                getattr(r, 'cpf', '') or '',
                getattr(r, 'parentesco', '') or '',
                getattr(r, 'telefone', '') or '',
                getattr(r, 'email', '') or '',
            ])
        t_resp = Table(rows, colWidths=[5*cm, 3*cm, 3*cm, 3*cm, 6*cm])
        t_resp.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#dddddd')),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONT', (0,0), (-1,-1), 'Helvetica', 9),
        ]))
        story.append(t_resp)

    # Seção: Saúde
    if saude:
        story.append(Paragraph("Saúde", h3))
        dados_saude = [
            ["Necessidade especial", "Sim" if getattr(saude, 'possui_necessidade_especial', False) else "Não"],
            ["Descrição", getattr(saude, 'descricao_necessidade', '') or ""],
            ["Usa medicação", "Sim" if getattr(saude, 'usa_medicacao', False) else "Não"],
            ["Quais", getattr(saude, 'quais_medicacoes', '') or ""],
            ["Alergia", "Sim" if getattr(saude, 'possui_alergia', False) else "Não"],
            ["Descrição alergia", getattr(saude, 'descricao_alergia', '') or ""],
        ]
        t_saude = Table(dados_saude, colWidths=[6*cm, 9*cm])
        t_saude.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#dddddd')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
        ]))
        story.append(t_saude)

    # Seção: Transporte
    if transporte:
        story.append(Paragraph("Transporte Escolar", h3))
        dados_transp = [
            ["Usa transporte", "Sim" if getattr(transporte, 'usa_transporte_escolar', False) else "Não"],
            ["Trajeto/Ponto", getattr(transporte, 'trajeto', '') or ""],
        ]
        t_transp = Table(dados_transp, colWidths=[6*cm, 9*cm])
        t_transp.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#dddddd')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
        ]))
        story.append(t_transp)

    # Seção: Autorizações
    if autorizacoes:
        story.append(Paragraph("Autorizações", h3))
        dados_auto = [
            ["Pode sair sozinho", "Sim" if getattr(autorizacoes, 'autorizacao_saida_sozinho', False) else "Não"],
            ["Permite fotos/eventos", "Sim" if getattr(autorizacoes, 'autorizacao_fotos_eventos', False) else "Não"],
            ["Pessoas autorizadas a buscar", getattr(autorizacoes, 'pessoa_autorizada_buscar', '') or ""],
        ]
        t_auto = Table(dados_auto, colWidths=[6*cm, 9*cm])
        t_auto.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#dddddd')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
        ]))
        story.append(t_auto)

    doc.build(story)

    pdf = buf.getvalue()
    buf.close()
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="aluno_{aluno_id}.pdf"'
    return resp


@login_required
@role_required(['diretor', 'coordenador'])
def cadastrar_aluno(request):
    request.session['matricula_gerada'] = gerar_matricula_unica()

    turmas = Turma.objects.filter(escola=request.escola
).order_by('nome')
    niveis_modalidades = ['Infantil', 'Fundamental I', 'Fundamental II']

    TIPOS_SANGUINEOS = [
        'A+', 'A-',
        'B+', 'B-',
        'AB+', 'AB-',
        'O+', 'O-',
    ]

    return render(request, 'pages/registrar_aluno.html', {
        'matricula': request.session['matricula_gerada'],
        'turmas': turmas,
        'niveis_modalidades': niveis_modalidades,
        'tipos_sanguineos': TIPOS_SANGUINEOS,  # 👈 ESSENCIAL
        'modo': 'create',
    })


@csrf_exempt
def editar_aluno(request, aluno_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            aluno = Aluno.objects.get(id=aluno_id, escola=request.escola
)

            # Atualiza dados principais do aluno
            aluno.nome = data.get('nome', aluno.nome)
            aluno.email = data.get('email', aluno.email)
            aluno.telefone = data.get('telefone', aluno.telefone)
            aluno.save()

            # Atualiza dados do responsável (se existirem)
            responsavel = Responsavel.objects.filter(aluno=aluno, escola=request.escola
).first()
            if responsavel:
                responsavel.nome = data.get('responsavel_nome', responsavel.nome)
                responsavel.cpf = data.get('responsavel_cpf', responsavel.cpf)
                responsavel.parentesco = data.get('responsavel_parentesco', responsavel.parentesco)
                responsavel.telefone = data.get('responsavel_telefone', responsavel.telefone)
                responsavel.email = data.get('responsavel_email', responsavel.email)
                responsavel.save()

            # Atualiza dados de saúde
            saude = Saude.objects.filter(aluno=aluno, escola=request.escola
).first()
            if saude:
                saude.possui_necessidade_especial = data.get('possui_necessidade_especial', saude.possui_necessidade_especial)
                saude.descricao_necessidade = data.get('descricao_necessidade', saude.descricao_necessidade)
                saude.usa_medicacao = data.get('usa_medicacao', saude.usa_medicacao)
                saude.quais_medicacoes = data.get('quais_medicacoes', saude.quais_medicacoes)
                saude.possui_alergia = data.get('possui_alergia', saude.possui_alergia)
                saude.descricao_alergia = data.get('descricao_alergia', saude.descricao_alergia)
                saude.save()

            # Atualiza transporte escolar
            transporte = TransporteEscolar.objects.filter(aluno=aluno, escola=request.escola
).first()
            if transporte:
                transporte.usa_transporte_escolar = data.get('usa_transporte_escolar', transporte.usa_transporte_escolar)
                transporte.trajeto = data.get('trajeto', transporte.trajeto)
                transporte.save()

            # Atualiza autorizações
            autorizacoes = Autorizacoes.objects.filter(aluno=aluno, escola=request.escola
).first()
            if autorizacoes:
                autorizacoes.autorizacao_saida_sozinho = data.get('autorizacao_saida_sozinho', autorizacoes.autorizacao_saida_sozinho)
                autorizacoes.autorizacao_fotos_eventos = data.get('autorizacao_fotos_eventos', autorizacoes.autorizacao_fotos_eventos)
                autorizacoes.pessoa_autorizada_buscar = data.get('pessoa_autorizada_buscar', autorizacoes.pessoa_autorizada_buscar)
                autorizacoes.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Método inválido'})


@login_required
@role_required(['diretor', 'coordenador'])
def editar_aluno_view(request, aluno_id):
    # ===============================
    # ALUNO (obrigatório)
    # ===============================
    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=request.escola

    )

    # Segurança extra
    if aluno.escola != request.escola:
        return HttpResponseForbidden("Acesso negado")

    # ===============================
    # RESPONSÁVEIS (CORRETO)
    # ===============================
    pai = Responsavel.objects.filter(
        aluno=aluno,
        tipo='pai'
    ).first()

    mae = Responsavel.objects.filter(
        aluno=aluno,
        tipo='mae'
    ).first()

    responsavel = Responsavel.objects.filter(
        aluno=aluno,
        tipo='responsavel'
    ).first()

    # ===============================
    # OUTRAS RELAÇÕES
    # ===============================
    saude = Saude.objects.filter(aluno=aluno).first()
    transporte = TransporteEscolar.objects.filter(aluno=aluno).first()
    autorizacoes = Autorizacoes.objects.filter(aluno=aluno).first()

    # ===============================
    # AUXILIARES DE TELA
    # ===============================
    turmas = Turma.objects.filter(
        escola=request.escola

    ).order_by('nome')

    niveis_modalidades = [
        'Infantil',
        'Fundamental I',
        'Fundamental II'
    ]

    tipos_sanguineos = [
        'A+', 'A-',
        'B+', 'B-',
        'AB+', 'AB-',
        'O+', 'O-'
    ]

    # ===============================
    # RENDER
    # ===============================
    return render(request, 'pages/registrar_aluno.html', {
        'modo': 'edit',

        # principais
        'aluno': aluno,
        'matricula': aluno.matricula,

        # responsáveis
        'pai': pai,
        'mae': mae,
        'responsavel': responsavel,

        # outras relações
        'saude': saude,
        'transporte': transporte,
        'autorizacoes': autorizacoes,

        # auxiliares
        'turmas': turmas,
        'niveis_modalidades': niveis_modalidades,
        'tipos_sanguineos': tipos_sanguineos,
    })

@csrf_exempt
def alternar_status_aluno(request, aluno_id):
    if request.method == 'POST':
        try:
            aluno = Aluno.objects.get(id=aluno_id, escola=request.escola
)
            aluno.ativo = not aluno.ativo
            aluno.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Método inválido'})

from django.core.serializers.json import DjangoJSONEncoder
import json

def _extrair_turma_info(aluno):
    """
    Tenta obter (id, nome, sigla, turno) da turma do aluno,
    cobrindo diferentes modelagens (FK direta, M2M, relação intermediária).
    Retorna (None, '', '', '') quando não houver turma.
    """
    # 1) FK direta: aluno.turma
    t = getattr(aluno, 'turma', None)
    if t:
        return getattr(t, 'id', None), getattr(t, 'nome', ''), getattr(t, 'sigla', ''), getattr(t, 'turno', '')

    # 2) M2M padrão: aluno.turmas / aluno.turma_set
    for rel_name in ('turmas', 'turma_set'):
        mgr = getattr(aluno, rel_name, None)
        if hasattr(mgr, 'all'):
            t = mgr.all().first()
            if t:
                return getattr(t, 'id', None), getattr(t, 'nome', ''), getattr(t, 'sigla', ''), getattr(t, 'turno', '')

    # 3) Relações intermediárias comuns que levam a uma turma
    #    (ajusta os nomes se o seu projeto usar outros)
    intermediarios = ('matriculas', 'matricula_set', 'alocacoes', 'alocacao_set', 'inscricoes', 'inscricao_set')
    for rel_name in intermediarios:
        mgr = getattr(aluno, rel_name, None)
        # checa se é RelatedManager/QuerySet
        if hasattr(mgr, 'select_related'):
            rel = mgr.select_related('turma').first()
            if rel is not None:
                t = getattr(rel, 'turma', None)
                if t:
                    return getattr(t, 'id', None), getattr(t, 'nome', ''), getattr(t, 'sigla', ''), getattr(t, 'turno', '')

    return None, '', '', ''

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import JsonResponse

from home.models import Aluno, Responsavel, TurmaDisciplina, Turma


# ============================================================
# FUNÇÃO: obter turmas do professor logado
# ============================================================
def turmas_do_professor(user):
    return Turma.objects.filter(
        disciplinas__professor=user
    ).distinct()


# ============================================================
# VIEW PRINCIPAL – LISTAGEM
# ============================================================
@login_required
def listar_alunos(request):

    escola = request.escola

    base_template = get_base_template(request)  # 👈 novo
    alunos = (
        Aluno.objects
        .filter(escola=escola)
        .select_related("turma_principal")
        .prefetch_related("responsaveis")
    )

    lista = []

    for a in alunos:
        lista.append({
            "id": a.id,
            "nome": a.nome,
            "matricula": a.matricula,
            "ativo": a.ativo,
            "dia_vencimento": a.dia_vencimento,
            "data_nascimento": (
                a.data_nascimento.isoformat()
                if a.data_nascimento else None
            ),
            "sexo": a.sexo,
            "rua": a.rua,
            "numero": a.numero,
            "cep": a.cep,
            "bairro": a.bairro,
            "cidade": a.cidade,
            "estado": a.estado,
            "possui_necessidade_especial": a.possui_necessidade_especial,

            "turma": {
                "nome": a.turma_principal.nome if a.turma_principal else "",
                "sigla": (
                    a.turma_principal.nome[:3].upper()
                    if a.turma_principal else ""
                ),
            },

            "responsaveis": [
                {
                    "id": r.id,
                    "nome": r.nome,
                    "cpf": r.cpf,
                    "tipo": r.tipo,
                    "parentesco": r.parentesco,
                    "telefone": r.telefone,
                    "email": r.email,
                    "identidade": r.identidade,
                    "escolaridade": r.escolaridade,
                    "profissao": r.profissao,
                }
                for r in a.responsaveis.all()
            ]
        })

    turmas_usuario = []
    if request.user.role == "professor":
        turmas_usuario = list(
            request.user.professor_turmas
            .values_list("nome", flat=True)
        )

    return render(
        request,
        "pages/listar_alunos.html",
        {
            "base_template": base_template, 
            "alunos_json": json.dumps(lista, ensure_ascii=False),
            "turmas_usuario": json.dumps(
                turmas_usuario,
                ensure_ascii=False
            ),
        }
    )

# ============================================================
# ATIVAR / INATIVAR ALUNO
# ============================================================
@login_required
def toggle_aluno_ativo(request, aluno_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido"}, status=405)

    escola = request.escola


    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=escola
    )

    aluno.ativo = not aluno.ativo
    aluno.save(update_fields=["ativo"])

    return JsonResponse({
        "success": True,
        "ativo": aluno.ativo
    })


@login_required
@require_POST
def excluir_aluno(request, aluno_id):
    escola = request.escola


    aluno = get_object_or_404(
        Aluno,
        id=aluno_id,
        escola=escola
    )

    # 🔒 Validações impeditivas
    if Presenca.objects.filter(aluno=aluno).exists():
        return JsonResponse({
            "success": False,
            "reason": "presenca",
            "message": "Aluno possui registros de presença."
        }, status=400)

    if RegistroPedagogico.objects.filter(aluno=aluno).exists():
        return JsonResponse({
            "success": False,
            "reason": "registro_pedagogico",
            "message": "Aluno possui registros pedagógicos."
        }, status=400)

    if aluno.turmas.exists():
        return JsonResponse({
            "success": False,
            "reason": "turmas",
            "message": "Aluno está vinculado a turmas."
        }, status=400)

    # ✅ Exclusão segura
    aluno.delete()

    return JsonResponse({
        "success": True
    })


@csrf_exempt  # ou use um decorator de CSRF seguro se for AJAX autenticado
@require_POST
def buscar_pessoa(request):
    try:
        data = json.loads(request.body)
        nome = data.get("nome", "").strip()
        tipo = data.get("tipo", "").lower()

        if not nome or tipo not in ["aluno", "professor"]:
            return JsonResponse({"error": "Parâmetros inválidos"}, status=400)

        if tipo == "professor":
            professores = Docente.objects.filter(nome__icontains=nome, escola=request.escola
).order_by("nome")
            resultados = [
                {"nome": p.nome, "disciplina": p.disciplina or "Disciplina não informada"} for p in professores
            ]
        else:
            alunos = Aluno.objects.filter(nome__icontains=nome, escola=request.escola
).order_by("nome")
            resultados = [{"nome": a.nome} for a in alunos]

        return JsonResponse({"resultados": resultados})
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# =====================================
#  AUTOCOMPLETE PESSOA (RESTRITO POR PERFIL)
# =====================================

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q


@login_required
def autocomplete_pessoa(request):
    termo = request.GET.get("nome", "").strip().lower()
    tipo = request.GET.get("tipo", "").strip().lower()

    user = request.user
    escola = user.escola

    if not termo:
        return JsonResponse([], safe=False)

    termo_norm = termo.replace(".", "").replace("-", "").replace(" ", "")

    # ------------------------------------------------------
    # AUTOCOMPLETE PARA PROFESSOR
    # ------------------------------------------------------
    if tipo == "professor":
        qs = Docente.objects.filter(escola=escola)

        qs = qs.filter(
            Q(nome__icontains=termo) |
            Q(cpf__icontains=termo_norm)
        )[:10]

        resp = [{
            "id": p.id,
            "nome": p.nome,
            "cpf": p.cpf,
            "tipo": "professor"
        } for p in qs]

        return JsonResponse(resp, safe=False)

    # ------------------------------------------------------
    # AUTOCOMPLETE PARA ALUNO
    # ------------------------------------------------------
    qs = Aluno.objects.filter(escola=escola)

    qs = qs.filter(
        Q(nome__icontains=termo) |
        Q(cpf__icontains=termo_norm) |
        Q(matricula__icontains=termo)
    )[:10]

    resp = [{
        "id": a.id,
        "nome": a.nome,
        "matricula": a.matricula,
        "cpf": a.cpf,
        "tipo": "aluno"
    } for a in qs]

    return JsonResponse(resp, safe=False)

@login_required
@require_POST
def criar_turma(request):
    escola = request.escola


    # ✅ JSON seguro
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "mensagem": "JSON inválido."}, status=400)

    nome = (data.get("nome") or "").strip()
    turno = (data.get("turno") or "").strip()
    ano = data.get("ano")
    sala = (data.get("sala") or "").strip()
    descricao = (data.get("descricao") or "").strip()

    professor_id = data.get("professor_id")
    disciplina_id = data.get("disciplina_id")
    alunos_ids = data.get("alunos_ids", [])

    # ✅ NOVO: sistema de avaliação (NUM/CON)
    sistema = (data.get("sistema_avaliacao") or "NUM").strip().upper()
    if sistema not in ("NUM", "CON"):
        sistema = "NUM"

    # 🔒 validação mínima (mantém seu comportamento)
    if not all([nome, turno, ano, sala]):
        return JsonResponse({
            "success": False,
            "mensagem": "Nome, turno, ano e sala são obrigatórios."
        }, status=400)

    # 🔒 ano int
    try:
        ano = int(ano)
        if ano < 2000 or ano > 2100:
            raise ValueError()
    except Exception:
        return JsonResponse({"success": False, "mensagem": "Ano inválido."}, status=400)

    # 🔒 alunos_ids deve ser lista
    if alunos_ids is None:
        alunos_ids = []
    if not isinstance(alunos_ids, list):
        return JsonResponse({"success": False, "mensagem": "alunos_ids deve ser uma lista."}, status=400)

    # 🔒 professor/disciplinas (se vierem, valida se são da escola)
    professor = None
    if professor_id:
        professor = Docente.objects.filter(id=professor_id, escola=escola, ativo=True).first()
        if not professor:
            return JsonResponse({"success": False, "mensagem": "Professor inválido."}, status=400)

    disciplina = None
    if disciplina_id:
        disciplina = Disciplina.objects.filter(id=disciplina_id, escola=escola).first()
        if not disciplina:
            return JsonResponse({"success": False, "mensagem": "Disciplina inválida."}, status=400)

    # 🔒 se vier um, tem que vir o outro (mantém lógica “somente se vier completo”)
    if (professor_id and not disciplina_id) or (disciplina_id and not professor_id):
        return JsonResponse({
            "success": False,
            "mensagem": "Para vincular, informe professor_id e disciplina_id."
        }, status=400)

    # ✅ TRANSAÇÃO: não cria turma pela metade
    try:
        with transaction.atomic():

            # 1️⃣ cria a turma
            turma = Turma.objects.create(
                nome=nome,
                turno=turno,
                ano=ano,
                sala=sala,
                descricao=descricao,
                escola=escola,
                sistema_avaliacao=sistema,   # ✅ NOVO
            )

            # 2️⃣ cria vínculo pedagógico SOMENTE se vier completo
            if professor and disciplina:
                # evita duplicação de vínculo (unique_together pode estourar)
                ja_existe = TurmaDisciplina.objects.filter(
                    turma=turma,
                    professor=professor,
                    disciplina=disciplina
                ).exists()

                if not ja_existe:
                    TurmaDisciplina.objects.create(
                        turma=turma,
                        professor=professor,
                        disciplina=disciplina,
                        escola=escola
                    )

            # 3️⃣ adiciona alunos (se vierem) - blindado por escola e ativo
            if alunos_ids:
                alunos = Aluno.objects.filter(
                    id__in=alunos_ids,
                    escola=escola,
                    ativo=True
                )

                alunos_map = {a.id: a for a in alunos}

                invalidos = [aid for aid in alunos_ids if int(aid) not in alunos_map]
                if invalidos:
                    return JsonResponse({
                        "success": False,
                        "mensagem": f"Alunos inválidos ou fora da escola: {invalidos}"
                    }, status=400)

                for aluno in alunos:
                    aluno.turmas.add(turma)

                    if not aluno.turma_principal:
                        aluno.turma_principal = turma
                        aluno.save(update_fields=['turma_principal'])

            return JsonResponse({
                "success": True,
                "mensagem": "Turma criada com sucesso!",
                "turma_id": turma.id,
                "sistema_avaliacao": sistema
            })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "mensagem": f"Erro ao criar turma: {str(e)}"
        }, status=400)
    

@login_required
@role_required(['diretor', 'coordenador'])
def formulario_criar_turma(request):
    escola = request.escola

    disciplinas = Disciplina.objects.filter(escola=escola).order_by('nome')

    return render(request, 'pages/registrar_turma.html', {
        'disciplinas': disciplinas,
        'avaliacao_choices': [("NUM", "Numérica (nota)"), ("CON", "Conceito (E/O/B)")],
    })

@login_required
@role_required(['diretor', 'coordenador'])
def impressao_dados(request):
    tipo = request.GET.get('tipo', 'turmas')
    turma_id = request.GET.get('turma')
    professor_id = request.GET.get('professor')
    dados = []

    if tipo == 'turmas':
        turmas = (
            Turma.objects
            .filter(escola=request.escola
)
            .prefetch_related('alunos', 'professores')
        )
        if turma_id:
            turmas = turmas.filter(id=turma_id)
        if professor_id:
            turmas = turmas.filter(professores__id=professor_id)

        dados = [{
            'nome': t.nome,
            'sala': t.sala,
            'turno': t.turno,
            'ano': t.ano,
            'professor': ', '.join([p.nome for p in t.professores.all()]) if t.professores.exists() else '—',
            'qtd_alunos': t.alunos.count()
        } for t in turmas]

    elif tipo == 'alunos':
        # Precarrega turmas + TODOS os responsáveis do aluno
        alunos = (
            Aluno.objects
            .filter(escola=request.escola
)
            .prefetch_related(
                'turmas',
                Prefetch('responsavel_set', queryset=Responsavel.objects.all(), to_attr='responsaveis')
            )
        )
        if turma_id:
            alunos = alunos.filter(turmas__id=turma_id)
        if professor_id:
            alunos = alunos.filter(turmas__professores__id=professor_id)

        dados = []
        for a in alunos:
            responsaveis = getattr(a, 'responsaveis', []) or []

            # tenta achar por marcadores
            pai = next((r for r in responsaveis if _is_pai(r)), None)
            mae = next((r for r in responsaveis if _is_mae(r)), None)

            # evita colisão (mesmo registro para os dois)
            if pai and mae and pai.pk == mae.pk:
                mae = next((r for r in responsaveis if r.pk != pai.pk and _is_mae(r)), None)

            # fallbacks para quando não há marcação
            if not mae and len(responsaveis) >= 2 and pai:
                mae = next((r for r in responsaveis if r.pk != getattr(pai, 'pk', None)), None)
            if not pai and not mae and len(responsaveis) >= 2:
                pai, mae = responsaveis[0], responsaveis[1]
            elif not pai and responsaveis:
                pai = responsaveis[0]  # mostra pelo menos um

            dados.append({
                'nome': a.nome,
                'cpf': a.cpf,
                'turma': ', '.join([t.nome for t in a.turmas.all()]) if hasattr(a, 'turmas') and a.turmas.exists() else '—',
                'telefone': a.telefone,

                # Pai / Mãe explícitos na listagem
                'pai': getattr(pai, 'nome', '') or '—',
                'pai_telefone': getattr(pai, 'telefone', '') or '',
                'mae': getattr(mae, 'nome', '') or '—',
                'mae_telefone': getattr(mae, 'telefone', '') or '',

                # Campo "responsavel" genérico (mantido para compatibilidade de template)
                'responsavel': (
                    (getattr(pai, 'nome', '') or getattr(mae, 'nome', '')) or
                    (responsaveis[0].nome if responsaveis else '—')
                ),
            })

    elif tipo == 'professores':
        professores = (
            Docente.objects
            .filter(escola=request.escola
)
            .prefetch_related("disciplinas")
        )
        dados = [{
            'nome': p.nome,
            'cpf': p.cpf,
            'disciplinas': ', '.join([d.nome for d in p.disciplinas.all()]),
            'email': p.email,
            'cargo': p.cargo
        } for p in professores]

    elif tipo == 'funcionarios':
        funcionarios = Funcionario.objects.filter(escola=request.escola
)
        dados = [{
            'nome': f.nome,
            'cpf': f.cpf,
            'cargo': f.cargo,
            'telefone': f.telefone,
            'email': f.email
        } for f in funcionarios]

    # Selects de filtro
    turmas_disponiveis = Turma.objects.filter(escola=request.escola
)
    professores_disponiveis = Docente.objects.filter(escola=request.escola
)

    context = {
        'tipo': tipo,
        'dados': dados,
        'turmas_disponiveis': turmas_disponiveis,
        'professores_disponiveis': professores_disponiveis,
        'turma_id': turma_id,
        'professor_id': professor_id,
    }
    return render(request, 'pages/print.html', context)



@csrf_exempt
@login_required
@role_required(['professor', 'diretor', 'coordenador'])
def lancar_notas(request):

    # GET apenas renderiza página
    if request.method == "GET":
        return render(request, "pages/registrar_notas.html")

    if request.method != "POST":
        return JsonResponse({"erro": "Método não permitido."}, status=405)

    try:

        dados = json.loads(request.body)

        turma_id = dados.get("turma_id")
        disciplina_id = dados.get("disciplina_id")
        bimestre = dados.get("bimestre")
        notas = dados.get("notas", {})

        if not turma_id or not disciplina_id:
            return JsonResponse(
                {"erro": "Turma e disciplina são obrigatórias."},
                status=400
            )

        if not bimestre:
            return JsonResponse(
                {"erro": "Bimestre é obrigatório."},
                status=400
            )

        try:
            bimestre = int(bimestre)
        except ValueError:
            return JsonResponse({"erro": "Bimestre inválido."}, status=400)

        escola = request.escola


        try:
            turma = Turma.objects.get(id=turma_id, escola=escola, status="ATIVA")
            disciplina = Disciplina.objects.get(id=disciplina_id, escola=escola)
        except (Turma.DoesNotExist, Disciplina.DoesNotExist):
            return JsonResponse({"erro": "Turma ou disciplina inválida."}, status=400)

        salvas = 0

        for aluno_id_str, notas_aluno in (notas or {}).items():

            try:
                aluno_id = int(aluno_id_str)
                aluno = Aluno.objects.get(id=aluno_id, escola=escola)
            except (ValueError, Aluno.DoesNotExist):
                continue

            if not isinstance(notas_aluno, dict):
                continue

            for avaliacao_id_str, valor in notas_aluno.items():

                try:
                    avaliacao_id = int(avaliacao_id_str)
                except (ValueError, TypeError):
                    continue

                # busca avaliação válida
                avaliacao = Avaliacao.objects.filter(
                    id=avaliacao_id,
                    turma=turma,
                    disciplina=disciplina,
                    escola=escola,
                    bimestre=bimestre
                ).first()

                if not avaliacao:
                    continue

                # bloqueia valor vazio
                if valor is None or str(valor).strip() == "":
                    continue

                valor_str = str(valor).strip().replace(",", ".")

                try:
                    valor_dec = Decimal(valor_str)
                except (InvalidOperation, TypeError, ValueError):
                    continue

                # salva nota
                Nota.objects.update_or_create(
                    aluno=aluno,
                    avaliacao=avaliacao,
                    defaults={
                        "valor": valor_dec,
                        "escola": escola
                    }
                )

                salvas += 1

        total_alunos = len(notas or {})

        if salvas == 0:
            return JsonResponse({
                "mensagem": "Nenhuma nota foi informada. Você pode salvar parcialmente."
            })

        if salvas < total_alunos:
            faltantes = total_alunos - salvas
            return JsonResponse({
                "mensagem": f"Notas salvas com sucesso ({salvas} lançadas). {faltantes} aluno(s) sem nota."
             })

        return JsonResponse({
            "mensagem": f"Notas salvas com sucesso ({salvas} lançadas)."
})
    except Exception as e:
        return JsonResponse(
            {"erro": f"Erro ao processar: {str(e)}"},
            status=400
        )


@login_required
@role_required(['professor', 'diretor', 'coordenador'])
def registrar_notas(request):

    user = request.user
    turma_id = request.GET.get('turma')
    disciplina_id = request.GET.get('disciplina')
    bimestre = request.GET.get('bimestre')

    escola = user.escola

    professor = Docente.objects.filter(user=user, escola=escola).first()

    if professor and user.role == 'professor':

        relacoes = TurmaDisciplina.objects.filter(
            professor=professor,
            turma__escola=escola
        ).select_related('turma', 'disciplina')

    else:

        relacoes = TurmaDisciplina.objects.filter(
            turma__escola=escola
        ).select_related('turma', 'disciplina')

    # LISTA DE TURMAS
    turmas = Turma.objects.filter(
        turmadisciplina__in=relacoes,
        escola=escola
    ).distinct().order_by('nome')

    # DISCIPLINAS
    if turma_id:

        if professor and user.role == 'professor':

            disciplinas = Disciplina.objects.filter(
                turmadisciplina__turma_id=turma_id,
                turmadisciplina__professor=professor,
                escola=escola
            ).distinct().order_by('nome')

        else:

            disciplinas = Disciplina.objects.filter(
                turmadisciplina__turma_id=turma_id,
                escola=escola
            ).distinct().order_by('nome')

    else:

        disciplinas = Disciplina.objects.filter(
            turmadisciplina__in=relacoes,
            escola=escola
        ).distinct().order_by('nome')

    alunos = []
    avaliacoes = []
    notas_dict = {}
    medias = {}

    turma_sistema_avaliacao = "NUM"

    if turma_id and disciplina_id and bimestre:

        turma = get_object_or_404(Turma, id=turma_id, escola=escola)
        disciplina = get_object_or_404(Disciplina, id=disciplina_id, escola=escola)

        turma_sistema_avaliacao = (
            getattr(turma, "sistema_avaliacao", None) or "NUM"
        ).upper()

        alunos = Aluno.objects.filter(turma_principal=turma, escola=escola).only('id', 'nome').order_by('nome')

        try:
            bimestre = int(bimestre)
        except (ValueError, TypeError):
            bimestre = None

        if bimestre:

            if not Avaliacao.objects.filter(
                turma=turma,
                disciplina=disciplina,
                escola=escola,
                bimestre=bimestre
            ).exists():

                modelos = ModeloAvaliacao.objects.filter(
                    disciplina=disciplina,
                    escola=escola,
                    ativo=True
                )

                for modelo in modelos:

                    Avaliacao.objects.get_or_create(
                        turma=turma,
                        disciplina=disciplina,
                        tipo=modelo.tipo,
                        descricao=modelo.nome,
                        bimestre=bimestre,
                        defaults={
                            "data": timezone.now().date(),
                            "escola": escola
                        }
                    )

            avaliacoes = Avaliacao.objects.filter(
                turma=turma,
                disciplina=disciplina,
                escola=escola,
                bimestre=bimestre
            ).select_related('tipo').only(
                'id',
                'descricao',
                'tipo__peso'
            ).order_by('data')

            avaliacoes_ids = list(
                avaliacoes.values_list('id', flat=True)
            )

            pesos_por_avaliacao = {}

            for av in avaliacoes:
                try:
                    pesos_por_avaliacao[av.id] = Decimal(
                        str(av.tipo.peso if av.tipo and av.tipo.peso else 1)
                    )
                except:
                    pesos_por_avaliacao[av.id] = Decimal("1")

            if avaliacoes_ids:

                todas_notas = Nota.objects.filter(
                    escola=escola,
                    avaliacao__bimestre=bimestre,
                    aluno_id__in=[a.id for a in alunos],
                    avaliacao_id__in=avaliacoes_ids
                ).only(
                    'aluno_id',
                    'avaliacao_id',
                    'valor'
                )

                for n in todas_notas:
                    if n.aluno_id not in notas_dict:
                        notas_dict[n.aluno_id] = {}

                    notas_dict.setdefault(n.aluno_id, {})[n.avaliacao_id] = n.valor

            if turma_sistema_avaliacao == "NUM":

                for aluno in alunos:

                    aluno_notas = notas_dict.get(aluno.id, {})

                    numerador = Decimal("0")
                    denominador = Decimal("0")

                    for av_id in avaliacoes_ids:

                        v = aluno_notas.get(av_id)

                        if v is None:
                            continue

                        try:
                            valor_dec = Decimal(str(v))
                        except:
                            continue

                        peso = pesos_por_avaliacao.get(av_id, Decimal("1"))

                        numerador += (valor_dec * peso)
                        denominador += peso

                    if denominador > 0:

                        media_calculada = (
                            numerador / denominador
                        ).quantize(
                            Decimal("0.1"),
                            rounding=ROUND_HALF_UP
                        )

                        # 🔥 AQUI A CORREÇÃO CERTA
                        medias[aluno.id] = arredondar_media_personalizada(media_calculada)

                    else:
                        medias[aluno.id] = None

            else:
                for aluno in alunos:
                    medias[aluno.id] = None

    context = {
        'turmas': turmas,
        'disciplinas': disciplinas,
        'alunos': alunos,
        'turma_id': turma_id or '',
        'disciplina_id': disciplina_id or '',
        'avaliacoes': avaliacoes,
        'notas': notas_dict,
        'medias': medias,
        'turma_sistema_avaliacao': turma_sistema_avaliacao,
    }

    return render(request, 'pages/registrar_notas.html', context)



def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')



def login_view(request):

    if request.user.is_authenticated:
        return redirect('index')

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST':

        identificador = request.POST.get("username", "").replace(".", "").replace("-", "")
        senha = request.POST.get("password")
        escola_id = request.POST.get("escola_id")
        ip = get_client_ip(request)

        # 🔥 busca por CPF
        try:
            user_obj = User.objects.get(cpf=identificador)
            username = user_obj.username
        except User.DoesNotExist:
            username = identificador
            user_obj = None

        user = authenticate(request, username=username, password=senha)

        if user is None:
            LoginLog.objects.create(
                user=user_obj,
                cpf=identificador,
                ip=ip,
                sucesso=False
            )

            form.add_error(None, "CPF ou senha inválidos")
            return render(request, 'pages/login.html', {'form': form})

        # ✅ login OK
        login(request, user)

        LoginLog.objects.create(
            user=user,
            cpf=identificador,
            ip=ip,
            sucesso=True
        )

        vinculos = UserEscola.objects.filter(user=user)

        # 🔥 MULTI ESCOLA → MOSTRA TELA
        if vinculos.count() > 1 and not escola_id:

            return render(request, 'pages/escolher_escola.html', {
                "escolas": vinculos
            })

        # 🔥 DEFINE ESCOLA
        if escola_id:
            request.session["escola_id"] = int(escola_id)

        elif vinculos.exists():
            request.session["escola_id"] = vinculos.first().escola.id

        elif getattr(user, "escola", None):
            request.session["escola_id"] = user.escola.id

        request.session.save()

        # 🔥 senha temporária
        if user.senha_temporaria:
            return redirect('trocar_senha')

        return redirect('index')

    return render(request, 'pages/login.html', {'form': form})



def logout_view(request):
    logout(request)
    return redirect('/')


@csrf_exempt
def cadastrar_funcionario_banco(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            nome = data.get('nome', '').strip()
            cpf = data.get('cpf', '').strip()
            rg = data.get('rg', '').strip()
            sexo = data.get('sexo', '').strip()
            data_nascimento = parse_date(data.get('data_nascimento'))
            estado_civil = data.get('estado_civil', '').strip()
            escolaridade = data.get('escolaridade', '').strip()
            turno_trabalho = data.get('turno_trabalho', '').strip()
            carga_horaria = data.get('carga_horaria', '').strip()
            tipo_vinculo = data.get('tipo_vinculo', '').strip()
            observacoes = data.get('observacoes', '').strip()
            cep = data.get('cep', '').strip()
            endereco = data.get('endereco', '').strip()
            numero = data.get('numero', '').strip()
            complemento = data.get('complemento', '').strip()
            bairro = data.get('bairro', '').strip()
            cidade = data.get('cidade', '').strip()
            estado = data.get('estado', '').strip()
            telefone = data.get('telefone', '').strip()
            email = data.get('email', '').strip()
            cargo = data.get('cargo', '').strip()
            ativo = to_bool(data.get('ativo', 'True'))

            funcionario = Funcionario.objects.create(
                nome=nome,
                cpf=cpf,
                rg=rg,
                sexo=sexo,
                data_nascimento=data_nascimento,
                estado_civil=estado_civil,
                escolaridade=escolaridade,
                turno_trabalho=turno_trabalho,
                carga_horaria=carga_horaria,
                tipo_vinculo=tipo_vinculo,
                observacoes=observacoes,
                cep=cep,
                endereco=endereco,
                numero=numero,
                complemento=complemento,
                bairro=bairro,
                cidade=cidade,
                estado=estado,
                telefone=telefone,
                email=email,
                cargo=cargo,
                ativo=ativo
            )

            # Criação do usuário caso cargo seja "secretaria"
            if cargo.lower() == 'secretaria':
                criar_usuario_com_cpf(
                    cpf=cpf,
                    senha=data.get('senha', 'senha@123'),
                    role='secretaria',
                    escola=None,
                    email=email,
                    is_staff=True
                )

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Erro ao cadastrar funcionário: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)



@login_required
@role_required(['diretor', 'coordenador'])
def importar_alunos(request):
    if request.method == 'POST' and request.FILES.get('arquivo'):
        arquivo = request.FILES['arquivo']

        try:
            df = pd.read_excel(arquivo)

            obrigatorios = ['nome', 'cpf', 'data_nascimento', 'email', 'telefone', 'cep', 'rua', 'numero', 'bairro', 'cidade', 'estado']
            for campo in obrigatorios:
                if campo not in df.columns:
                    messages.error(request, f"O campo obrigatório '{campo}' não foi encontrado na planilha.")
                    return redirect('importar_alunos')

            criados = 0
            ignorados = 0

            with transaction.atomic():
                for _, row in df.iterrows():
                    cpf = str(row.get('cpf')).replace('.', '').replace('-', '').strip()
                    if Aluno.objects.filter(cpf=cpf, escola=request.escola
).exists():
                        ignorados += 1
                        continue

                    data_nasc = row.get('data_nascimento')
                    if isinstance(data_nasc, str):
                        data_nasc = datetime.strptime(data_nasc, "%Y-%m-%d")

                    aluno = Aluno.objects.create(
                        nome=row.get('nome', '').strip(),
                        cpf=cpf,
                        data_nascimento=data_nasc,
                        email=row.get('email', '').strip(),
                        telefone=row.get('telefone', '').strip(),
                        cep=row.get('cep', '').strip(),
                        rua=row.get('rua', '').strip(),
                        numero=str(row.get('numero', '')).strip(),
                        bairro=row.get('bairro', '').strip(),
                        cidade=row.get('cidade', '').strip(),
                        estado=row.get('estado', '').strip()
                    )

                    if row.get('responsavel_nome'):
                        Responsavel.objects.create(
                            aluno=aluno,
                            nome=row.get('responsavel_nome', '').strip(),
                            cpf=str(row.get('responsavel_cpf', '')).strip(),
                            telefone=row.get('responsavel_telefone', '').strip(),
                            email=row.get('responsavel_email', '').strip()
                        )

                    criados += 1

            messages.success(request, f"✅ {criados} aluno(s) importado(s) com sucesso. {ignorados} já existiam.")
        except Exception as e:
            messages.error(request, f"Erro ao processar a planilha: {str(e)}")

        return redirect('importar_alunos')

    return render(request, 'pages/importar_alunos.html')


@login_required
def verificar_senha_temporaria(request):
    if request.user.senha_temporaria:
        return render(request, 'pages/trocar_senha.html')
    return redirect('index')



def trocar_senha_api(request):

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método inválido"})

    data = json.loads(request.body)

    nova_senha = data.get("nova_senha")
    confirmar = data.get("nova_senha_confirmar")
    token = data.get("token")

    if nova_senha != confirmar:
        return JsonResponse({"success": False, "error": "Senhas não coincidem"})

    # 🔐 senha forte
    erro_senha = validar_senha_forte(nova_senha)
    if erro_senha:
        return JsonResponse({"success": False, "error": erro_senha})

    user = None

    # 🔥 fluxo 1: reset com token
    if token:
        try:
            token_obj = PasswordResetToken.objects.get(token=token)

            if token_obj.is_expired():
                token_obj.delete()
                return JsonResponse({"success": False, "error": "Token expirado"})

            user = token_obj.user

            # 🔥 invalida todos os tokens desse usuário
            PasswordResetToken.objects.filter(user=user).delete()

        except PasswordResetToken.DoesNotExist:
            return JsonResponse({"success": False, "error": "Token inválido"})

    # 🔥 fluxo 2: usuário logado
    elif request.user.is_authenticated:
        user = request.user

    else:
        return JsonResponse({"success": False, "error": "Não autorizado"})

    # 🔐 atualiza senha
    user.set_password(nova_senha)
    user.senha_temporaria = False
    user.save()

    # 🔥 LOGIN AUTOMÁTICO (importantíssimo)
    login(request, user)

    return JsonResponse({"success": True})


@login_required
@role_required(['diretor', 'coordenador'])
def listar_turmas_para_boletim(request):

    turma_id = request.GET.get('turma')
    print("TURMA_ID:", turma_id)

    turmas = Turma.objects.filter(escola=request.escola
)

    alunos = []

    if turma_id:

        alunos = Aluno.objects.filter(
            notas__avaliacao__turma_id=turma_id,
            escola=request.escola

        ).distinct().order_by("nome")


    return render(request, 'pages/listar_turmas_boletim.html', {
        'turmas': turmas,
        'alunos': alunos,
        'turma_id': turma_id
    })


from collections import defaultdict
from datetime import datetime

@login_required
@role_required(['diretor', 'coordenador'])
def visualizar_boletim(request, aluno_id):

    aluno = get_object_or_404(Aluno, pk=aluno_id)
    escola = aluno.escola

    # 🔥 BUSCA TODAS AS NOTAS DO ALUNO
    notas = Nota.objects.filter(
        aluno=aluno,
        escola=escola
    ).select_related(
        'avaliacao__disciplina',
        'avaliacao__tipo',
        'avaliacao__turma'
    )

    # 🔥 DEFINE A TURMA BASEADA NAS NOTAS
    turma = None
    if notas.exists():
        turma = notas.first().avaliacao.turma

    # 🔥 ESTRUTURA BASE (AGORA COM NOTAS)
    dados = defaultdict(lambda: {
        "bimestres": {1: None, 2: None, 3: None, 4: None},
        "notas": {1: [], 2: [], 3: [], 4: []},  # 👈 NOVO
        "media_final": None
    })

    # 🔥 ORGANIZA AS NOTAS (AGORA AGRUPANDO)
    for nota in notas:

        disciplina = nota.avaliacao.disciplina.nome
        bimestre = nota.avaliacao.bimestre

        if nota.valor is not None:

            # 👇 adiciona na lista (NÃO sobrescreve mais)
            dados[disciplina]["notas"][bimestre].append({
                "tipo": getattr(nota.avaliacao.tipo, "nome", "Avaliação"),
                "valor": float(nota.valor)
            })

    boletim = []

    # 🔥 PROCESSA MÉDIAS
    for disciplina, info in dados.items():

        medias_bimestre = {}

        for bimestre in [1, 2, 3, 4]:

            lista_notas = info["notas"][bimestre]

            if lista_notas:
                valores = [n["valor"] for n in lista_notas]
                media = sum(valores) / len(valores)
                medias_bimestre[bimestre] = arredondar_media_personalizada(media)
            else:
                medias_bimestre[bimestre] = None

        # 🔥 MÉDIA FINAL
        valores_validos = [
            v for v in medias_bimestre.values()
            if v is not None
        ]

        media_final = None
        if valores_validos:
            media_final = sum(valores_validos) / len(valores_validos)
            media_final = arredondar_media_personalizada(media_final)

        boletim.append({
            "disciplina": disciplina,
            "bimestres": medias_bimestre,
            "notas": info["notas"],  # 👈 ESSENCIAL
            "media_final": media_final,
            "faltas": 0  # mantém compatibilidade com template
        })

    return render(request, 'pages/boletim.html', {
        'aluno': aluno,
        'turma': turma,
        'escola': escola,
        'ano': datetime.now().year,
        'boletim': boletim
    })


@csrf_exempt
@login_required
@transaction.atomic
def cadastrar_disciplina(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nome = data.get('nome', '').strip()

            if not nome:
                return JsonResponse({'success': False, 'error': 'Nome da disciplina é obrigatório.'}, status=400)

            escola = request.escola

            if not escola:
                return JsonResponse({'success': False, 'error': 'Usuário sem escola vinculada.'}, status=400)

            # Verifica se já existe disciplina com o mesmo nome para essa escola
            if Disciplina.objects.filter(nome__iexact=nome, escola=escola).exists():
                return JsonResponse({'success': False, 'error': 'Essa disciplina já está cadastrada.'}, status=400)

            Disciplina.objects.create(nome=nome, escola=escola)

            return JsonResponse({'success': True, 'mensagem': 'Disciplina cadastrada com sucesso.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Erro interno: {str(e)}'}, status=500)

    return JsonResponse({'success': False, 'error': 'Método não permitido.'}, status=405)


def pagina_cadastrar_disciplina(request):
    return render(
        request,
        'pages/cadastrar_disciplinas.html'
    )

@login_required
def usuario_sem_escola(request):
    return render(request, 'pages/erro_sem_escola.html')

@login_required
def visualizar_escola(request):
    escola = request.escola

    estados = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
        'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ]
    return render(request, 'pages/escola_detalhes.html', {
        'escola': escola,
        'estados': estados
    })

@csrf_exempt
@login_required
def editar_escola(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            escola = request.escola


            campos_permitidos = ['nome', 'telefone', 'email', 'endereco', 'numero', 'complemento',
                                 'bairro', 'cidade', 'estado', 'site', 'cep']

            for campo in campos_permitidos:
                if campo in data:
                    setattr(escola, campo, data[campo])

            escola.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)



@csrf_exempt
@login_required
@transaction.atomic
def salvar_turma(request):

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método inválido'}, status=405)

    try:

        data = request.POST

        nome = data.get('nome', '').strip()
        turno = data.get('turno', '').strip()
        ano = data.get('ano', '').strip()
        sala = data.get('sala', '').strip()
        descricao = data.get('descricao', '').strip()

        turma_id = data.get('turma_id') or request.GET.get('turma_id')

        if turma_id:
            turma_id = int(turma_id)
        else:
            turma_id = None

        alunos_ids = [x for x in request.POST.getlist('alunos_ids') if x]

        if not (nome and turno and ano and sala):
            return JsonResponse({
                'success': False,
                'error': 'Nome, turno, ano e sala são obrigatórios.'
            }, status=400)

        escola = request.escola


        # =========================================================
        # 🔹 CRIAR OU ATUALIZAR TURMA
        # =========================================================

        if turma_id:

            turma = Turma.objects.get(id=turma_id, escola=escola)

            turma.nome = nome
            turma.turno = turno
            turma.ano = ano
            turma.sala = sala
            turma.descricao = descricao
            turma.save()

        else:

            turma = Turma.objects.create(
                nome=nome,
                turno=turno,
                ano=ano,
                sala=sala,
                descricao=descricao,
                escola=escola
            )

        # =========================================================
        # 🔹 ALUNOS
        # =========================================================

        if alunos_ids:
            turma.alunos.clear()
            alunos = Aluno.objects.filter(id__in=alunos_ids, escola=escola)
            turma.alunos.add(*alunos)

        # =========================================================
        # 🔹 PROFESSORES + DISCIPLINAS
        # =========================================================

        prof_disc = request.POST.get("prof_disc")

        if prof_disc:

            TurmaDisciplina.objects.filter(turma=turma).delete()

            lista = json.loads(prof_disc)

            for item in lista:

                TurmaDisciplina.objects.create(
                    turma=turma,
                    professor_id=int(item["professor_id"]),
                    disciplina_id=int(item["disciplina_id"]),
                    escola=escola
                )

        # =========================================================
        # 🔥 DISCIPLINAS DA TURMA
        # =========================================================

        disciplinas = Disciplina.objects.filter(
            turmadisciplina__turma=turma
        ).distinct()

        # =========================================================
        # 🔥 GARANTIR TIPOS DE AVALIAÇÃO
        # =========================================================

        tipo_prova, _ = TipoAvaliacao.objects.get_or_create(
            escola=escola,
            nome="Prova"
        )

        tipo_trabalho, _ = TipoAvaliacao.objects.get_or_create(
            escola=escola,
            nome="Trabalho"
        )

        # =========================================================
        # 🔥 GARANTIR MODELOS POR DISCIPLINA
        # =========================================================

        for disciplina in disciplinas:

            if not ModeloAvaliacao.objects.filter(
                escola=escola,
                disciplina=disciplina
            ).exists():

                ModeloAvaliacao.objects.create(
                    nome="Prova",
                    tipo=tipo_prova,
                    peso=7,
                    escola=escola,
                    disciplina=disciplina,
                    ativo=True
                )

                ModeloAvaliacao.objects.create(
                    nome="Trabalho",
                    tipo=tipo_trabalho,
                    peso=3,
                    escola=escola,
                    disciplina=disciplina,
                    ativo=True
                )

        # =========================================================
        # 🔥 GERAR AVALIAÇÕES
        # =========================================================

        ja_existe = Avaliacao.objects.filter(turma=turma).exists()

        if not ja_existe:

            bimestres = [1, 2, 3, 4]

            for disciplina in disciplinas:

                modelos = ModeloAvaliacao.objects.filter(
                    escola=escola,
                    disciplina=disciplina,
                    ativo=True
                )

                for bimestre in bimestres:

                    for modelo in modelos:

                        Avaliacao.objects.get_or_create(
                            turma=turma,
                            disciplina=disciplina,
                            bimestre=bimestre,
                            descricao=modelo.nome,
                            escola=escola,
                            defaults={
                                "tipo": modelo.tipo,
                                "data": timezone.now().date()
                            }
                        )

        # =========================================================

        return JsonResponse({
            'success': True,
            'turma_id': turma.id
        })

    except Exception as e:

        import traceback
        traceback.print_exc()

        transaction.set_rollback(True)

        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def listar_disciplinas(request):
    disciplinas = Disciplina.objects.all().values('id', 'nome')
    return JsonResponse({'disciplinas': list(disciplinas)})


@csrf_exempt
def editar_disciplina(request):
    data = json.loads(request.body)
    try:
        disciplina = Disciplina.objects.get(id=data['id'])
        disciplina.nome = data['nome']
        disciplina.save()
        return JsonResponse({'success': True})
    except:
        return JsonResponse({'success': False})

@csrf_exempt
def excluir_disciplina(request):
    data = json.loads(request.body)
    try:
        Disciplina.objects.get(id=data['id']).delete()
        return JsonResponse({'success': True})
    except:
        return JsonResponse({'success': False})


@login_required
@role_required(["diretor", "coordenador", "professor"])
def diario_classe(request):
    user = request.user
    today = date.today()

    contexto = {
        "today": today,
    }

    if user.role == "professor":
        docente = user.docente

        turmas = (
            TurmaDisciplina.objects
            .filter(professor=docente)
            .select_related("turma")
            .values("turma__id", "turma__nome")
            .distinct()
        )

        contexto["turmas"] = [
            {"id": t["turma__id"], "nome": t["turma__nome"]}
            for t in turmas
        ]

    else:
        turmas = Turma.objects.filter(escola=user.escola)
        contexto["turmas"] = turmas

    return render(request, "pages/diario_classe.html", contexto)



@require_POST
@login_required
def salvar_chamada(request):
    data = json.loads(request.body)
    turma_id = data['turma_id']
    disciplina_id = data['disciplina_id']
    presencas = data['presencas']

    professor = request.user.docente

    # Evita duplicação: uma chamada por dia, por professor/turma/disciplina
    chamada_existente = Chamada.objects.filter(
        data=date.today(),
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor=professor
    ).first()

    if chamada_existente:
        return JsonResponse({'success': False, 'erro': 'Chamada já registrada para hoje.'}, status=400)

    chamada = Chamada.objects.create(
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor=professor
    )

    for p in presencas:
        Presenca.objects.create(
            chamada=chamada,
            aluno_id=p['aluno_id'],
            presente=p['presente'],
            observacao=p['observacao']
        )

    return JsonResponse({'success': True})


@login_required
@role_required('professor,diretor,coordenador')
def buscar_alunos(request, turma_id):
    turma = get_object_or_404(Turma, id=turma_id)
    alunos = turma.alunos.filter(ativo=True)
    
    alunos_serializados = [
        {"id": aluno.id, "nome": aluno.nome}
        for aluno in alunos
    ]

    return JsonResponse({
        "alunos": alunos_serializados
    })

@login_required
@require_POST
@csrf_exempt  # opcional se você já passa o CSRFToken no fetch
def editar_registro(request, registro_id):
    try:
        data = json.loads(request.body)
        presente = data.get('presente')
        observacao = data.get('observacao', '')

        registro = Presenca.objects.select_related('chamada').get(id=registro_id)

        # Verifica se o professor é dono da chamada
        if request.user.role == 'professor' and registro.chamada.professor.user != request.user:
            return JsonResponse({'sucesso': False, 'erro': 'Sem permissão para editar este registro'}, status=403)

        registro.presente = presente
        registro.observacao = observacao
        registro.save()

        return JsonResponse({'sucesso': True})

    except Presenca.DoesNotExist:
        return JsonResponse({'sucesso': False, 'erro': 'Registro não encontrado'}, status=404)

    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)

def visualizar_chamada(request):
    user = request.user
    turma_id = request.GET.get('turma')
    disciplina_id = request.GET.get('disciplina')
    data_filtro = request.GET.get('data')

    presencas = Presenca.objects.select_related(
        'chamada', 'aluno', 'chamada__disciplina', 'chamada__turma', 'chamada__professor'
    )

    if user.role == 'professor':
        try:
            docente = user.docente
            presencas = presencas.filter(chamada__professor=docente)

            turmas_vinculadas = TurmaDisciplina.objects.filter(professor=docente).select_related('turma', 'disciplina')
            turmas = [td.turma for td in turmas_vinculadas]
            disciplinas = list({td.disciplina for td in turmas_vinculadas})  # evita duplicatas

        except Docente.DoesNotExist:
            return render(request, 'pages/visualizar_diario.html', {
                'erro': 'Usuário sem vínculo com docente.'
            })
    else:
        presencas = presencas.all()
        turmas = Turma.objects.all()
        disciplinas = Disciplina.objects.all()

    if turma_id:
        presencas = presencas.filter(chamada__turma_id=turma_id)
    if disciplina_id:
        presencas = presencas.filter(chamada__disciplina_id=disciplina_id)
    if data_filtro:
        presencas = presencas.filter(chamada__data=data_filtro)

    contexto = {
        'registros': presencas,
        'turmas': turmas,
        'disciplinas': disciplinas,
    }

    return render(request, 'pages/visualizar_diario.html', contexto)

@csrf_exempt
@require_POST
@login_required
def editar_registro(request, registro_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            presente = data.get('presente') == 'True'
            observacao = data.get('observacao')

            presenca = Presenca.objects.get(id=registro_id)
            presenca.presente = presente
            presenca.observacao = observacao
            presenca.save()

            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    
    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido'})


@login_required
def listar_turmas(request):
    qs = Turma.objects.all()

    # filtra por escola, se houver escola vinculada
    if 'escola' in [f.name for f in Turma._meta.fields] and getattr(request.user, 'escola', None):
        qs = qs.filter(escola=request.escola
)

    qs = qs.order_by('nome')

    turmas = []
    for t in qs:
        turmas.append({
            'id': t.id,
            'nome': t.nome or '',
            'turno': t.turno or '',
            'ano': t.ano,                 # inteiro
            'sala': t.sala or '',
            'descricao': t.descricao or '',

            # ✅ NOVO: para o modal abrir corretamente
            'sistema_avaliacao': getattr(t, "sistema_avaliacao", "NUM") or "NUM",
        })

    context = {
        'turmas_json': json.dumps(turmas, cls=DjangoJSONEncoder, ensure_ascii=False)
    }
    return render(request, 'pages/listar_turmas.html', context)


def _coerce_for_field(value, field: models.Field):
    if value in ("", None):
        return None if field.null else (0 if isinstance(field, models.IntegerField) else "")
    if isinstance(field, models.IntegerField):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError(f"Valor inválido para {field.name}: esperado inteiro.")
    if isinstance(field, (models.CharField, models.TextField)):
        return str(value)
    return value


@login_required
@require_http_methods(["POST"])
def editar_turma(request, pk):
    qs = Turma.objects

    if 'escola' in [f.name for f in Turma._meta.fields] and getattr(request.user, 'escola', None):
        turma = get_object_or_404(qs, pk=pk, escola=request.escola
)
    else:
        turma = get_object_or_404(qs, pk=pk)

    # ✅ Agora usamos POST em vez de JSON
    data = request.POST

    # campos permitidos para edição
    allowed = ['nome', 'sala', 'ano', 'turno', 'descricao', 'sistema_avaliacao']

    updated = {}

    for field_name in allowed:
        if field_name in data:
            field = Turma._meta.get_field(field_name)

            try:
                coerced = _coerce_for_field(data.get(field_name), field)
            except ValueError as e:
                return JsonResponse(
                    {'success': False, 'error': str(e)},
                    status=400
                )

            # validação específica do sistema de avaliação
            if field_name == "sistema_avaliacao":
                coerced = (str(coerced).strip().upper() if coerced is not None else "NUM")

                if coerced not in ("NUM", "CON"):
                    return JsonResponse(
                        {
                            'success': False,
                            'error': 'sistema_avaliacao inválido. Use "NUM" ou "CON".'
                        },
                        status=400
                    )

            setattr(turma, field_name, coerced)
            updated[field_name] = coerced

    try:
        with transaction.atomic():
            turma.save()

    except Exception as e:
        return JsonResponse(
            {
                'success': False,
                'error': f'Erro ao salvar turma: {str(e)}'
            },
            status=400
        )

    return JsonResponse({
        'success': True,
        'turma': {
            'id': turma.id,
            'nome': turma.nome or '',
            'sala': turma.sala or '',
            'ano': turma.ano,
            'turno': turma.turno or '',
            'descricao': turma.descricao or '',
            'sistema_avaliacao': getattr(turma, "sistema_avaliacao", "NUM") or "NUM",
        },
        'updated_fields': list(updated.keys()),
    })

@login_required
@require_http_methods(["POST"])
def excluir_turma(request, pk):
    qs = Turma.objects
    if hasattr(Turma, 'escola_id') or 'escola' in [f.name for f in Turma._meta.fields]:
        turma = get_object_or_404(qs, pk=pk, escola=request.escola
)
    else:
        turma = get_object_or_404(qs, pk=pk)
    turma.delete()
    return JsonResponse({'success': True})

def _data_por_extenso(dt):
    try:
        import locale
        for loc in ("pt_BR.UTF-8","pt_BR.utf8","pt_BR","pt_BR.ISO8859-1"):
            try:
                locale.setlocale(locale.LC_TIME, loc)
                break
            except locale.Error:
                continue
        return dt.strftime("%d de %B de %Y")
    except Exception:
        return dt.strftime("%d/%m/%Y")

def _norm(s):
    return (s or "").strip().casefold()

def _is_pai(resp):
    return _norm(getattr(resp, "tipo", "")) == "pai" or _norm(getattr(resp, "parentesco", "")) == "pai"

def _is_mae(resp):
    t = _norm(getattr(resp, "tipo", ""))
    p = _norm(getattr(resp, "parentesco", ""))
    return t in ("mae", "mãe") or p in ("mae", "mãe")

@login_required
def aluno_requerimento_pdf(request, pk):
    qs = Aluno.objects.select_related("escola").prefetch_related("turmas")
    aluno = (
        get_object_or_404(qs, pk=pk, escola=request.escola
)
        if hasattr(Aluno, "escola_id")
        else get_object_or_404(qs, pk=pk)
    )
    hoje_extenso = format_date(date.today(), "d 'de' MMMM 'de' y", locale="pt_BR")

    # ======= Helpers =======
    def _case(s):
        return (s or "").strip().casefold()

    def is_pai(r):
        return _case(r.tipo) == "pai" or _case(r.parentesco) == "pai"

    def is_mae(r):
        return _case(r.tipo) in ("mae", "mãe") or _case(r.parentesco) in ("mae", "mãe")

    # ======= Carrega responsáveis =======
    todos = list(Responsavel.objects.filter(aluno=aluno).order_by("id"))

    pai = next((r for r in todos if is_pai(r)), None)
    mae = next((r for r in todos if is_mae(r)), None)

    # ======= Responsável (não pai/mãe) =======
    resp = next(
        (r for r in todos if r not in (pai, mae)),
        None
    )

    # ======= Relacionamentos =======
    saude = Saude.objects.filter(aluno=aluno).first()
    transporte = TransporteEscolar.objects.filter(aluno=aluno).first()
    autoriz = Autorizacoes.objects.filter(aluno=aluno).first()

    # ======= Contexto =======
    ctx = {
        "aluno": aluno,

        # pai
        "dados_pai": pai,

        # mae
        "dados_mae": mae,

        # responsável
        "dados_resp": resp,

        # extras
        "saude": saude,
        "transporte": transporte,
        "autoriz": autoriz,
        "hoje_extenso": hoje_extenso,
    }


    return render(request, "pages/aluno_ficha_impressao.html", ctx)



def create_admin_temp(request):
    # segurança mínima para não ficar público
    if not settings.DEBUG:
        return HttpResponse("Somente permitido em modo DEBUG", status=403)

    User = get_user_model()

    if User.objects.filter(username="admin").exists():
        return HttpResponse("Admin já existe.")

    User.objects.create(
        username="goutemberg",
        cpf="05356145438",
        nome="goutemberg",
        email="goutemberg@icloud.com",
        password=make_password("Gps34587895@&*"),
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )

    return HttpResponse("Superusuário criado com sucesso!")


def reimprimir_documentos_aluno(request):
    
    return render(request, 'pages/reimprimir_documentos.html')


def comprovante_matricula_pdf(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk, escola=request.escola
)
    return render(request, "pages/comprovante_matricula.html", {"aluno": aluno})


def ficha_cadastral_pdf(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk, escola=request.escola
)

    dados_pai = Responsavel.objects.filter(aluno=aluno, tipo__iexact="pai").first()
    dados_mae = Responsavel.objects.filter(aluno=aluno, tipo__iexact="mae").first()
    dados_resp = Responsavel.objects.filter(aluno=aluno).exclude(tipo__in=["pai", "mae"]).first()

    print("===== DEBUG VIEW =====")
    print("Aluno:", aluno.id, aluno.nome)
    print("Responsáveis:", list(Responsavel.objects.filter(aluno=aluno).values("id","nome","tipo","parentesco")))
    print("dados_pai:", dados_pai)
    print("dados_mae:", dados_mae)
    print("dados_resp:", dados_resp)
    print("======================")

    saude = getattr(aluno, "saude", None)
    transporte = getattr(aluno, "transporte", None)
    autoriz = getattr(aluno, "autorizacoes", None)

    hoje_extenso = datetime.now().strftime("%d de %B de %Y")

    context = {
        "aluno": aluno,
        "dados_pai": dados_pai,
        "dados_mae": dados_mae,
        "dados_resp": dados_resp,
        "saude": saude,
        "transporte": transporte,
        "autoriz": autoriz,
        "hoje_extenso": hoje_extenso,
    }

    return render(request, "pages/aluno_ficha_impressao.html", context)


def pagina_nome_turma(request):
    return render(request, "pages/nome_turma.html")


def cadastrar_nome_turma(request):
    data = json.loads(request.body)
    nome = data.get("nome")

    if NomeTurma.objects.filter(nome=nome, escola=request.escola
).exists():
        return JsonResponse({"success": False, "error": "Nome já cadastrado."})

    NomeTurma.objects.create(nome=nome, escola=request.escola
)
    return JsonResponse({"success": True})


def listar_nomes_turma(request):
    nomes = NomeTurma.objects.filter(escola=request.escola
).values("id", "nome")
    return JsonResponse({"nomes": list(nomes)})


def editar_nome_turma(request):
    data = json.loads(request.body)

    try:
        id = int(data.get("id"))
    except:
        return JsonResponse({"success": False, "error": "ID inválido."})

    nome = data.get("nome")

    obj = NomeTurma.objects.filter(
        id=id,
        escola=request.escola

    ).first()

    if not obj:
        return JsonResponse({"success": False, "error": "Registro não encontrado."})

    obj.nome = nome
    obj.save()

    return JsonResponse({"success": True})


def excluir_nome_turma(request):
    data = json.loads(request.body)
    id = data.get("id")

    NomeTurma.objects.filter(id=id, escola=request.escola
).delete()
    return JsonResponse({"success": True})


@login_required
def atualizar_vencimento(request, aluno_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            aluno = Aluno.objects.get(id=aluno_id, escola=request.escola)

            dia = data.get("dia_vencimento")
            aluno.dia_vencimento = int(dia) if dia else None
            aluno.save()

            return JsonResponse({"status": "ok"})

        except Exception as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": str(e)
            }, status=400)