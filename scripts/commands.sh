#!/bin/sh
set -e

echo ""
echo "==============================="
echo "🚀 ENTRYPOINT — Iniciando"
echo "==============================="
echo ""

# =============================================================
# 0) Ambiente
# =============================================================
DJANGO_ENV="${DJANGO_ENV:-dev}"

if [ "$DJANGO_ENV" = "prod" ]; then
    SETTINGS="plantao_pro.settings.prod"
    PORT="${PORT:-10000}"
else
    SETTINGS="plantao_pro.settings.dev"
    PORT="${PORT:-8000}"
fi

echo "🌎 Ambiente        = $DJANGO_ENV"
echo "⚙️ Settings        = $SETTINGS"
echo "🌐 Porta           = $PORT"
echo "🐍 Python          = $(python -V 2>&1)"
echo ""

# =============================================================
# 1) Esperar Postgres
# =============================================================
if [ -n "$DATABASE_URL" ]; then
    echo "⏳ Aguardando Postgres em: $DATABASE_URL"
    /scripts/wait_psql.sh "$DATABASE_URL"
else
    echo "⚠️ DATABASE_URL não definido — pulando wait..."
fi

echo ""

# =============================================================
# 2) Migrations
# =============================================================
echo "📦 Rodando migrations..."
python manage.py migrate --noinput --settings=$SETTINGS
echo "✔️ Migrations aplicadas!"
echo ""

# =============================================================
# 3) Superuser (apenas DEV)
# =============================================================
if [ "$DJANGO_ENV" != "prod" ]; then
    echo "👤 Criando superuser padrão (DEV)..."

    python manage.py shell --settings=$SETTINGS << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()

username = "05356145438"
email = "admin@example.com"
password = "admin34587895"

u = User.objects.filter(username=username).first()
if not u:
    User.objects.create_superuser(username=username, email=email, password=password)
    print("✔️ Superuser criado:", username)
else:
    print("ℹ️ Superuser já existe:", username)
EOF
fi

echo ""

# =============================================================
# 4) Static (IMPORTANTE)
# =============================================================
if [ "$DJANGO_ENV" = "prod" ]; then
    echo "📁 Executando collectstatic (PROD)..."
    python manage.py collectstatic --noinput --clear --settings=$SETTINGS
    echo "✔️ Static coletado!"
else
    echo "📁 DEV: pulando collectstatic"
fi

echo ""

# =============================================================
# 5) Start Server
# =============================================================
if [ "$DJANGO_ENV" = "prod" ]; then
    echo "🚀 Iniciando Gunicorn..."
    exec gunicorn plantao_pro.wsgi:application \
        --bind 0.0.0.0:$PORT \
        --workers=3
else
    echo "🚀 Iniciando Django DEV..."
    exec python manage.py runserver 0.0.0.0:$PORT --settings=$SETTINGS
fi