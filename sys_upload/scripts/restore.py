#!/usr/bin/env python3
"""
Script de restore do banco PostgreSQL rodando no Docker
Uso: python scripts/restore.py --file backup_20240101_120000.sql
"""
import os
import subprocess
import sys
import glob
from pathlib import Path
from datetime import datetime
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

def list_backups(backup_dir):
    """Lista todos os backups disponíveis"""
    backup_files = sorted(
        glob.glob(str(backup_dir / 'backup_*.sql')),
        key=os.path.getmtime,
        reverse=True
    )
    
    if not backup_files:
        print('📭 Nenhum backup encontrado')
        return []
    
    print(f'\n📂 Backups disponíveis ({len(backup_files)}):\n')
    for i, file_path in enumerate(backup_files, 1):
        filename = os.path.basename(file_path)
        size = os.path.getsize(file_path) / (1024 * 1024)
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        print(f'  {i}. {filename}  ({size:.2f} MB)  {mtime.strftime("%Y-%m-%d %H:%M:%S")}')
    
    return backup_files

def restore(backup_path, db_config):
    """Restaura um backup"""
    # Confirmação
    print(f'\n⚠️  ATENÇÃO: Isso irá SOBRESCREVER o banco de dados atual!')
    print(f'📁 Arquivo: {os.path.basename(backup_path)}')
    print(f'🗄️  Banco: {db_config["NAME"]} em {db_config["HOST"]}:{db_config["PORT"]}')
    
    confirm = input('\nDeseja continuar? (sim/não): ')
    if confirm.lower() != 'sim':
        print('❌ Restore cancelado')
        return
    
    # Comando psql
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['PASSWORD']
    
    cmd = [
        'psql',
        '-h', db_config['HOST'],
        '-p', str(db_config['PORT']),
        '-U', db_config['USER'],
        '-d', db_config['NAME'],
        '-f', str(backup_path)
    ]
    
    print('\n🔄 Restaurando backup...')
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print('✅ Backup restaurado com sucesso!')
        else:
            print(f'❌ Erro ao restaurar:')
            print(result.stderr)
            sys.exit(1)
            
    except FileNotFoundError:
        print('❌ psql não encontrado. Instale o PostgreSQL client:')
        print('   sudo apt install postgresql-client')
        sys.exit(1)
    except Exception as e:
        print(f'❌ Erro inesperado: {e}')
        sys.exit(1)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Restaura backup do banco de dados')
    parser.add_argument('--file', help='Nome do arquivo de backup')
    parser.add_argument('--list', action='store_true', help='Lista backups disponíveis')
    parser.add_argument('--latest', action='store_true', help='Restaura o backup mais recente')
    
    args = parser.parse_args()
    
    backup_dir = Path(__file__).parent.parent / 'backups'
    db_config = get_db_config()
    
    if args.list:
        list_backups(backup_dir)
        return
    
    if args.file:
        backup_path = backup_dir / args.file
        if not backup_path.exists():
            print(f'❌ Arquivo não encontrado: {backup_path}')
            sys.exit(1)
        restore(backup_path, db_config)
    elif args.latest:
        backups = list_backups(backup_dir)
        if backups:
            restore(backups[0], db_config)
        else:
            print('❌ Nenhum backup encontrado')
            sys.exit(1)
    else:
        print('❌ Especifique --file, --latest ou --list')
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()