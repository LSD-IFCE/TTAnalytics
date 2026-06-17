#!/bin/sh
set -e

# Inicia o Gunicorn (servidor WSGI)
echo "🚀 Iniciando Gunicorn..."
gunicorn --bind 0.0.0.0:8000 config.wsgi:application --workers 4 --threads 2 &

# Inicia o Nginx
echo "🌐 Iniciando Nginx..."
nginx -g "daemon off;"