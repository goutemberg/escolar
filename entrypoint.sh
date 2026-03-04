#!/bin/bash
set -e

echo "=== Nuke 1: Apagando staticfiles COMPLETO ==="
rm -rf /app/staticfiles
mkdir -p /app/staticfiles

echo "=== Nuke 2: Apagando staticfiles.json perdido ==="
find /app -name "staticfiles.json" -delete || true
find /tmp -name "staticfiles.json" -delete || true

echo "=== Nuke 3: Limpando cache Python ==="
find /app -name "__pycache__" -exec rm -rf {} + || true
find /app -name "*.pyc" -delete || true

echo "=== Rodando migrations ==="
python manage.py migrate --noinput --settings=plantao_pro.settings.prod

echo "=== Gerando staticfiles NOVO (do zero) ==="
python manage.py collectstatic --clear --noinput --settings=plantao_pro.settings.prod

echo "=== Iniciando servidor ==="
exec "$@"
