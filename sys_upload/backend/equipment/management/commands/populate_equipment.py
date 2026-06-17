from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from equipment.models import Brand, Rubber, Blade
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Popula o banco com madeiras e borrachas populares'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpa os equipamentos existentes antes de cadastrar',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('🗑️ Removendo equipamentos existentes...')
            Rubber.objects.all().delete()
            Blade.objects.all().delete()
            self.stdout.write('✅ Equipamentos removidos!')

        # Busca o primeiro usuário admin para ser o criador
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()
            if not admin_user:
                self.stdout.write(self.style.WARNING('⚠️ Nenhum usuário encontrado. Criando como "admin" padrão...'))
                admin_user = User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')

        self.stdout.write('📦 Cadastrando equipamentos populares...')

        def get_brand(brand_name):
            brand, _ = Brand.objects.get_or_create(name=brand_name, defaults={'is_active': True})
            return brand

        # ============================================
        # BORRACHAS POPULARES
        # ============================================
        rubbers = [
            # Butterfly
            {
                'name': 'Tenergy 05',
                'brand': 'Butterfly',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Vermelha',
                'description': 'Borracha mais famosa do mundo. Excelente para jogadores ofensivos e versáteis.'
            },
            {
                'name': 'Tenergy 64',
                'brand': 'Butterfly',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.FOREHAND,
                'thickness': '2.1mm',
                'color': 'Preta',
                'description': 'Maior velocidade que a Tenergy 05. Ideal para ataques rápidos.'
            },
            {
                'name': 'Tenergy 80',
                'brand': 'Butterfly',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.BACKHAND,
                'thickness': '2.1mm',
                'color': 'Preta',
                'description': 'Equilíbrio entre T05 e T64. Excelente para todos os estilos.'
            },
            {
                'name': 'Dignics 05',
                'brand': 'Butterfly',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Vermelha',
                'description': 'Borracha premium com grande rotação e controle.'
            },
            {
                'name': 'Dignics 09C',
                'brand': 'Butterfly',
                'category': Rubber.Category.TACKY,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Preta',
                'description': 'Borracha adesiva de alta performance. Combina rotação e velocidade.'
            },
            
            # DHS
            {
                'name': 'Hurricane 3 Neo',
                'brand': 'DHS',
                'category': Rubber.Category.TACKY,
                'rubber_type': Rubber.Type.FOREHAND,
                'thickness': '2.15mm',
                'color': 'Preta',
                'description': 'Borracha adesiva clássica. Alta rotação e controle.'
            },
            {
                'name': 'Hurricane 8',
                'brand': 'DHS',
                'category': Rubber.Category.HYBRID,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Vermelha',
                'description': 'Híbrida que combina aderência e velocidade. Excelente para jogadores modernos.'
            },
            {
                'name': 'Skyline 3',
                'brand': 'DHS',
                'category': Rubber.Category.TACKY,
                'rubber_type': Rubber.Type.FOREHAND,
                'thickness': '2.2mm',
                'color': 'Preta',
                'description': 'Borracha adesiva chinesa. Alta rotação e controle em curtos.'
            },
            
            # Tibhar
            {
                'name': 'MX-P',
                'brand': 'Tibhar',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Vermelha',
                'description': 'Borracha tensor com grande velocidade e rotação.'
            },
            {
                'name': 'FX-P',
                'brand': 'Tibhar',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.BACKHAND,
                'thickness': '2.0mm',
                'color': 'Preta',
                'description': 'Versão mais macia da MX-P. Ideal para backhand.'
            },
            {
                'name': 'EL-P',
                'brand': 'Tibhar',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Vermelha',
                'description': 'Equilíbrio entre velocidade e controle.'
            },
            {
                'name': 'Hybrid K3',
                'brand': 'Tibhar',
                'category': Rubber.Category.HYBRID,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Preta',
                'description': 'Borracha híbrida com aderência e tensor.'
            },

            # Andro
            {
                'name': 'Rasanter R47',
                'brand': 'Andro',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Vermelha',
                'description': 'Borracha tensor com grande rotação e dinâmica.'
            },
            {
                'name': 'Rasanter R42',
                'brand': 'Andro',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.BACKHAND,
                'thickness': '2.0mm',
                'color': 'Preta',
                'description': 'Versão mais macia da R47. Excelente para backhand.'
            },
            {
                'name': 'Hexer HD',
                'brand': 'Andro',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Vermelha',
                'description': 'Borracha tensor de alta durabilidade.'
            },
            
            # Stiga
            {
                'name': 'Mantra M',
                'brand': 'Stiga',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Vermelha',
                'description': 'Borracha tensor com excelente controle.'
            },
            {
                'name': 'Mantra H',
                'brand': 'Stiga',
                'category': Rubber.Category.TENSOR,
                'rubber_type': Rubber.Type.FOREHAND,
                'thickness': '2.1mm',
                'color': 'Preta',
                'description': 'Versão mais dura da Mantra. Maior velocidade.'
            },
            {
                'name': 'Genesis M',
                'brand': 'Stiga',
                'category': Rubber.Category.HYBRID,
                'rubber_type': Rubber.Type.UNIVERSAL,
                'thickness': '2.1mm',
                'color': 'Vermelha',
                'description': 'Borracha híbrida. Combina aderência chinesa com tensor.'
            },
        ]

        count = 0
        for rubber_data in rubbers:
            brand = get_brand(rubber_data['brand'])
            rubber, created = Rubber.objects.get_or_create(
                name=rubber_data['name'],
                brand=brand,
                defaults={
                    **{key: value for key, value in rubber_data.items() if key != 'brand'},
                    'brand': brand,
                    'created_by': admin_user,
                    'is_active': True
                }
            )
            if created:
                count += 1
                self.stdout.write(f'  ✅ {rubber.brand.name} {rubber.name}')
            else:
                self.stdout.write(f'  ℹ️ {rubber.brand.name} {rubber.name} já existe')

        self.stdout.write(self.style.SUCCESS(f'✅ {count} borrachas cadastradas!'))

        # ============================================
        # MADEIRAS POPULARES
        # ============================================
        blades = [
            # Butterfly
            {
                'name': 'Viscaria',
                'brand': 'Butterfly',
                'blade_type': Blade.Type.OFFENSIVE,
                'speed_class': Blade.SpeedClass.FAST,
                'weight': '85g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira mais famosa do mundo. Usada por muitos jogadores profissionais.'
            },
            {
                'name': 'Timo Boll ALC',
                'brand': 'Butterfly',
                'blade_type': Blade.Type.OFFENSIVE,
                'speed_class': Blade.SpeedClass.FAST,
                'weight': '88g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira com carbono ALC. Alta velocidade e controle.'
            },
            {
                'name': 'Zhang Jike ALC',
                'brand': 'Butterfly',
                'blade_type': Blade.Type.OFFENSIVE,
                'speed_class': Blade.SpeedClass.FAST,
                'weight': '87g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira ofensiva com carbono ALC.'
            },
            {
                'name': 'Primorac Carbon',
                'brand': 'Butterfly',
                'blade_type': Blade.Type.CARBON,
                'speed_class': Blade.SpeedClass.VERY_FAST,
                'weight': '90g',
                'layers': 3,
                'handle': 'Flare',
                'description': 'Madeira de carbono muito rápida.'
            },
            {
                'name': 'Hadraw 5',
                'brand': 'Butterfly',
                'blade_type': Blade.Type.ALLROUND,
                'speed_class': Blade.SpeedClass.MEDIUM,
                'weight': '82g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira all-round. Excelente para controle e desenvolvimento.'
            },
            
            # Stiga
            {
                'name': 'Clipper Wood',
                'brand': 'Stiga',
                'blade_type': Blade.Type.OFFENSIVE,
                'speed_class': Blade.SpeedClass.FAST,
                'weight': '85g',
                'layers': 7,
                'handle': 'Flare',
                'description': 'Madeira clássica de 7 camadas. Muito popular.'
            },
            {
                'name': 'Infinity VPS V',
                'brand': 'Stiga',
                'blade_type': Blade.Type.OFFENSIVE,
                'speed_class': Blade.SpeedClass.MEDIUM,
                'weight': '85g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira ofensiva com excelente feeling.'
            },
            {
                'name': 'Allround Classic',
                'brand': 'Stiga',
                'blade_type': Blade.Type.ALLROUND,
                'speed_class': Blade.SpeedClass.MEDIUM,
                'weight': '78g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira all-round clássica. Ótima para iniciantes.'
            },
            
            # Tibhar
            {
                'name': 'Samsonov Force Pro',
                'brand': 'Tibhar',
                'blade_type': Blade.Type.OFFENSIVE,
                'speed_class': Blade.SpeedClass.FAST,
                'weight': '87g',
                'layers': 7,
                'handle': 'Flare',
                'description': 'Madeira ofensiva de 7 camadas.'
            },
            {
                'name': 'Stratus Power Wood',
                'brand': 'Tibhar',
                'blade_type': Blade.Type.OFFENSIVE,
                'speed_class': Blade.SpeedClass.FAST,
                'weight': '85g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira com excelente relação velocidade/controle.'
            },
            {
                'name': 'Stratus Carbon',
                'brand': 'Tibhar',
                'blade_type': Blade.Type.CARBON,
                'speed_class': Blade.SpeedClass.FAST,
                'weight': '88g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira com carbono. Alta velocidade.'
            },
            
            # Andro
            {
                'name': 'Trello CF',
                'brand': 'Andro',
                'blade_type': Blade.Type.CARBON,
                'speed_class': Blade.SpeedClass.FAST,
                'weight': '86g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira com carbono para jogadores ofensivos.'
            },
            {
                'name': 'Kinetic Supreme',
                'brand': 'Andro',
                'blade_type': Blade.Type.OFFENSIVE,
                'speed_class': Blade.SpeedClass.MEDIUM,
                'weight': '83g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira com tecnologia Kinetic para melhor absorção de impacto.'
            },
            
            # DHS
            {
                'name': 'Hurricane Long 5',
                'brand': 'DHS',
                'blade_type': Blade.Type.OFFENSIVE,
                'speed_class': Blade.SpeedClass.FAST,
                'weight': '88g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira usada por Ma Long. Excelente para estilo ofensivo.'
            },
            {
                'name': 'Hurricane Hao 3',
                'brand': 'DHS',
                'blade_type': Blade.Type.OFFENSIVE,
                'speed_class': Blade.SpeedClass.MEDIUM,
                'weight': '85g',
                'layers': 5,
                'handle': 'Flare',
                'description': 'Madeira equilibrada. Ótima para jogadores agressivos.'
            },
        ]

        count = 0
        for blade_data in blades:
            brand = get_brand(blade_data['brand'])
            blade, created = Blade.objects.get_or_create(
                name=blade_data['name'],
                brand=brand,
                defaults={
                    **{key: value for key, value in blade_data.items() if key != 'brand'},
                    'brand': brand,
                    'created_by': admin_user,
                    'is_active': True
                }
            )
            if created:
                count += 1
                self.stdout.write(f'  ✅ {blade.brand.name} {blade.name}')
            else:
                self.stdout.write(f'  ℹ️ {blade.brand.name} {blade.name} já existe')

        self.stdout.write(self.style.SUCCESS(f'✅ {count} madeiras cadastradas!'))
        self.stdout.write(self.style.SUCCESS('🎉 População de equipamentos concluída!'))

        # Resumo
        total_rubbers = Rubber.objects.count()
        total_blades = Blade.objects.count()
        self.stdout.write(f'\n📊 Resumo:')
        self.stdout.write(f'  🏓 Borrachas: {total_rubbers}')
        self.stdout.write(f'  🏓 Madeiras: {total_blades}')