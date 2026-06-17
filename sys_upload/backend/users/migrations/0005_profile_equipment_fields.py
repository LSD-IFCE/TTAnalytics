from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0003_brand_foreign_keys'),
        ('users', '0004_profile_approval_status_profile_club_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='blade',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='profiles_using_blade', to='equipment.blade', verbose_name='Madeira'),
        ),
        migrations.AddField(
            model_name='profile',
            name='dominant_hand',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='profiles', to='equipment.handedness', verbose_name='Mão Dominante'),
        ),
        migrations.AddField(
            model_name='profile',
            name='grip',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='profiles', to='equipment.grip', verbose_name='Empunhadura'),
        ),
        migrations.AddField(
            model_name='profile',
            name='player_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='profiles', to='equipment.playertype', verbose_name='Tipo'),
        ),
        migrations.AddField(
            model_name='profile',
            name='rubber_1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='profiles_using_rubber_1', to='equipment.rubber', verbose_name='Borracha 1'),
        ),
        migrations.AddField(
            model_name='profile',
            name='rubber_2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='profiles_using_rubber_2', to='equipment.rubber', verbose_name='Borracha 2'),
        ),
    ]