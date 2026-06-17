#!/bin/sh
set -e

echo "🔄 Iniciando setup..."

# Aplica migrações
echo "🔄 Aplicando migrações..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Coleta arquivos estáticos
echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Cria superusuário se não existir (apenas em desenvolvimento)
if [ "$DEBUG" = "True" ]; then
    echo "👤 Criando superusuário padrão..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
    print('✅ Superusuário criado!')
else:
    print('ℹ️ Superusuário já existe.')
"
fi

echo "✅ Setup concluído!"

exec "$@"