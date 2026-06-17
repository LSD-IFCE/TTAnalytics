import os
import time
import psycopg2
from psycopg2 import OperationalError

def wait_for_db():
    """Aguarda o banco de dados ficar disponível"""
    db_name = os.getenv('DB_NAME', 'tenis_mesa')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres')
    db_host = os.getenv('DB_HOST', 'db')
    db_port = os.getenv('DB_PORT', '5432')
    
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(
                dbname=db_name,
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port
            )
            conn.close()
            print("✅ Banco de dados disponível!")
            return True
        except OperationalError:
            retry_count += 1
            print(f"⏳ Aguardando banco de dados... ({retry_count}/{max_retries})")
            time.sleep(2)
    
    print("❌ Banco de dados não disponível após várias tentativas")
    return False

if __name__ == "__main__":
    wait_for_db()