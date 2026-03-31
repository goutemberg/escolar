#!/usr/bin/env sh
set -e

echo "==> Iniciando Escolinha..."

# ======================================================
# Local do projeto
# ======================================================
cd /app

PORT="${PORT:-8000}"
PY=python
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-plantao_pro.settings.prod}"

echo "==> PORT=$PORT"
echo "==> DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"

# ======================================================
# MIGRATIONS
# ======================================================
echo "==> migrate"
$PY manage.py migrate --no-input

# ======================================================
# STATIC
# ======================================================
echo "==> collectstatic"
$PY manage.py collectstatic --no-input --clear

# ======================================================
# SERVER
# ======================================================
echo "==> subindo gunicorn"
exec $PY -m gunicorn plantao_pro.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers=3