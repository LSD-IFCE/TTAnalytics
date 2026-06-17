from django.db import migrations
from django.core.management import call_command
import os

def load_initial_data(apps, schema_editor):
    """
    Carrega os dados iniciais do arquivo fixture
    """
    try:
        # Models
        Grip = apps.get_model('equipment', 'Grip')
        Handedness = apps.get_model('equipment', 'Handedness')
        PlayerType = apps.get_model('equipment', 'PlayerType')
        
        # 1. Empunhaduras
        grips = [
            {'name': 'Clássico', 'description': 'Empunhadura clássica, também conhecida como Shakehand', 'is_active': True},
            {'name': 'Caneta', 'description': 'Empunhadura estilo caneta, também conhecida como Penhold', 'is_active': True},
            {'name': 'Classineta', 'description': 'Empunhadura mista, variação da caneta', 'is_active': True},
        ]
        for grip_data in grips:
            Grip.objects.get_or_create(name=grip_data['name'], defaults=grip_data)
        
        # 2. Mãos Dominantes
        handedness_list = [
            {'name': 'Destro', 'is_active': True},
            {'name': 'Canhoto', 'is_active': True},
            {'name': 'Ambidestro', 'is_active': True},
        ]
        for hand_data in handedness_list:
            Handedness.objects.get_or_create(name=hand_data['name'], defaults=hand_data)
        
        # 3. Tipos de Atleta
        types = [
            {'name': 'Ofensivo', 'description': 'Jogador com estilo de jogo ofensivo, prioriza ataques', 'is_active': True},
            {'name': 'Defensivo', 'description': 'Jogador com estilo de jogo defensivo, prioriza defesa', 'is_active': True},
            {'name': 'All-Rounded', 'description': 'Jogador com estilo equilibrado, ofensivo e defensivo', 'is_active': True},
        ]
        for type_data in types:
            PlayerType.objects.get_or_create(name=type_data['name'], defaults=type_data)
            
        print('✅ Dados iniciais carregados com sucesso!')
        
    except Exception as e:
        print(f'⚠️ Erro ao carregar dados: {e}')
        # Não levanta exceção para não quebrar a migração

def unload_initial_data(apps, schema_editor):
    """
    Remove os dados iniciais (opcional - para rollback)
    """
    # Models
    Grip = apps.get_model('equipment', 'Grip')
    Handedness = apps.get_model('equipment', 'Handedness')
    PlayerType = apps.get_model('equipment', 'PlayerType')
    
    # Remove os dados que foram criados
    Grip.objects.all().delete()
    Handedness.objects.all().delete()
    PlayerType.objects.all().delete()
    print('🗑️ Dados iniciais removidos.')

class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_initial_data, unload_initial_data),
    ]