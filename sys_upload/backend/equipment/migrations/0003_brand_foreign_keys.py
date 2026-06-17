from django.db import migrations, models
import django.db.models.deletion


def migrate_brands_forward(apps, schema_editor):
    Brand = apps.get_model('equipment', 'Brand')
    Rubber = apps.get_model('equipment', 'Rubber')
    Blade = apps.get_model('equipment', 'Blade')

    def normalize_brand(value):
        if value is None:
            return ''
        return value.strip()

    for model in (Rubber, Blade):
        for item in model.objects.all():
            brand_name = normalize_brand(item.legacy_brand)
            if not brand_name:
                continue

            brand, _ = Brand.objects.get_or_create(name=brand_name)
            item.brand = brand
            item.save(update_fields=['brand'])


def migrate_brands_backward(apps, schema_editor):
    Rubber = apps.get_model('equipment', 'Rubber')
    Blade = apps.get_model('equipment', 'Blade')

    for model in (Rubber, Blade):
        for item in model.objects.select_related('brand').all():
            item.legacy_brand = item.brand.name if item.brand else ''
            item.save(update_fields=['legacy_brand'])


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0002_load_initial_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nome')),
                ('is_active', models.BooleanField(default=True, verbose_name='Ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Marca',
                'verbose_name_plural': 'Marcas',
                'ordering': ['name'],
            },
        ),
        migrations.RenameField(
            model_name='rubber',
            old_name='brand',
            new_name='legacy_brand',
        ),
        migrations.RenameField(
            model_name='blade',
            old_name='brand',
            new_name='legacy_brand',
        ),
        migrations.AddField(
            model_name='rubber',
            name='brand',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rubbers', to='equipment.brand', verbose_name='Marca'),
        ),
        migrations.AddField(
            model_name='blade',
            name='brand',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='blades', to='equipment.brand', verbose_name='Marca'),
        ),
        migrations.RunPython(migrate_brands_forward, migrate_brands_backward),
        migrations.AlterModelOptions(
            name='rubber',
            options={'ordering': ['brand__name', 'name'], 'verbose_name': 'Borracha', 'verbose_name_plural': 'Borrachas'},
        ),
        migrations.AlterModelOptions(
            name='blade',
            options={'ordering': ['brand__name', 'name'], 'verbose_name': 'Madeira', 'verbose_name_plural': 'Madeiras'},
        ),
        migrations.AlterUniqueTogether(
            name='rubber',
            unique_together={('name', 'brand')},
        ),
        migrations.AlterUniqueTogether(
            name='blade',
            unique_together={('name', 'brand')},
        ),
        migrations.RemoveField(
            model_name='rubber',
            name='legacy_brand',
        ),
        migrations.RemoveField(
            model_name='blade',
            name='legacy_brand',
        ),
    ]