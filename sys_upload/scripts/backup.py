#!/usr/bin/env python3
"""
Script de backup do banco PostgreSQL rodando no Docker
Uso: python scripts/backup.py
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Caminho para o .env que está dentro de backend/
env_path = Path(__file__).parent.parent / 'backend' / '.env'
load_dotenv(env_path)

def get_db_config():
    """Pega configurações do banco do .env"""
    return {
        'NAME': os.getenv('DB_NAME', 'tenis_mesa'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST_HOST', 'localhost'),  # Para conexão do host
        'PORT': os.getenv('DB_PORT_HOST', '5433'),       # Porta mapeada no host
    }

def backup():
    """Faz backup do banco de dados"""
    db_config = get_db_config()
    
    # Pasta de backup na raiz do projeto
    backup_dir = Path(__file__).parent.parent / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    # Nome do arquivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backup_{timestamp}.sql"
    backup_path = backup_dir / backup_file
    
    # Comando pg_dump (roda no host)
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['PASSWORD']
    
    cmd = [
        'pg_dump',
        '-h', db_config['HOST'],
        '-p', str(db_config['PORT']),
        '-U', db_config['USER'],
        '-d', db_config['NAME'],
        '-F', 'p',  # Plain text
        '--clean',
        '--if-exists',
        '--no-owner',
        '--no-acl',
        '-f', str(backup_path)
    ]
    
    print(f'📦 Conectando ao banco: {db_config["HOST"]}:{db_config["PORT"]}')
    print(f'📁 Backup: {backup_path}')
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            size = backup_path.stat().st_size / (1024 * 1024)
            print(f'✅ Backup criado com sucesso! ({size:.2f} MB)')
            print(f'📁 Arquivo: {backup_file}')
            cleanup_old_backups(backup_dir, keep=10)
        else:
            print(f'❌ Erro ao criar backup:')
            print(result.stderr)
            sys.exit(1)
            
    except FileNotFoundError:
        print('❌ pg_dump não encontrado. Instale o PostgreSQL client:')
        print('   sudo apt install postgresql-client')
        sys.exit(1)
    except Exception as e:
        print(f'❌ Erro inesperado: {e}')
        sys.exit(1)

def cleanup_old_backups(backup_dir, keep=10):
    """Mantém apenas os N backups mais recentes"""
    import glob
    
    backup_files = sorted(
        glob.glob(str(backup_dir / 'backup_*.sql')),
        key=os.path.getmtime,
        reverse=True
    )
    
    if len(backup_files) > keep:
        for old_file in backup_files[keep:]:
            os.remove(old_file)
            print(f'🗑️  Removendo backup antigo: {os.path.basename(old_file)}')

if __name__ == '__main__':
    backup()