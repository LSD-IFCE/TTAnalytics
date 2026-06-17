from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

User = get_user_model()  # ← USA O MODELO CORRETO

# ============================================
# CADASTROS APENAS PARA ADMINISTRADORES
# ============================================

class Grip(models.Model):
    """
    Empunhadura (apenas Admin)
    """
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Nome'))
    description = models.TextField(blank=True, verbose_name=_('Descrição'))
    is_active = models.BooleanField(default=True, verbose_name=_('Ativo'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Empunhadura')
        verbose_name_plural = _('Empunhaduras')
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Handedness(models.Model):
    """
    Mão Dominante (apenas Admin)
    """
    name = models.CharField(max_length=20, unique=True, verbose_name=_('Nome'))
    is_active = models.BooleanField(default=True, verbose_name=_('Ativo'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Mão Dominante')
        verbose_name_plural = _('Mãos Dominantes')
        ordering = ['name']
    
    def __str__(self):
        return self.name

class PlayerType(models.Model):
    """
    Tipo de Atleta (apenas Admin)
    """
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Nome'))
    description = models.TextField(blank=True, verbose_name=_('Descrição'))
    is_active = models.BooleanField(default=True, verbose_name=_('Ativo'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Tipo de Atleta')
        verbose_name_plural = _('Tipos de Atletas')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Brand(models.Model):
    """
    Marca de equipamentos
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Nome'))
    is_active = models.BooleanField(default=True, verbose_name=_('Ativo'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Marca')
        verbose_name_plural = _('Marcas')
        ordering = ['name']

    def __str__(self):
        return self.name

# ============================================
# CADASTROS PARA ADMIN, TÉCNICOS E ATLETAS
# ============================================

class Rubber(models.Model):
    """
    Borracha (Admin, Técnico, Atleta)
    """
    # Categorias de borracha
    class Category(models.TextChoices):
        TACKY = 'TACKY', _('Adesiva')
        TENSOR = 'TENSOR', _('Tensor')
        HYBRID = 'HYBRID', _('Híbrida')
        ANTI = 'ANTI', _('Anti')
        CLASSIC = 'CLASSIC', _('Clássica')
    
    # Tipos de borracha
    class Type(models.TextChoices):
        FOREHAND = 'FH', _('Forehand')
        BACKHAND = 'BH', _('Backhand')
        UNIVERSAL = 'UNI', _('Universal')
    
    name = models.CharField(max_length=100, verbose_name=_('Nome'))
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rubbers',
        verbose_name=_('Marca')
    )
    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        default=Category.TENSOR,
        verbose_name=_('Categoria')
    )
    rubber_type = models.CharField(
        max_length=3,
        choices=Type.choices,
        default=Type.UNIVERSAL,
        verbose_name=_('Tipo')
    )
    thickness = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Espessura')
    )
    color = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Cor')
    )
    description = models.TextField(blank=True, verbose_name=_('Descrição'))
    is_active = models.BooleanField(default=True, verbose_name=_('Ativo'))
    created_by = models.ForeignKey(
        User,  # ← USA O MODELO CORRETO
        on_delete=models.SET_NULL,
        null=True,
        related_name='rubbers_created',
        verbose_name=_('Criado por')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Borracha')
        verbose_name_plural = _('Borrachas')
        ordering = ['brand__name', 'name']
        unique_together = ['name', 'brand']
    
    def __str__(self):
        return f"{self.brand} {self.name}" if self.brand else self.name

class Blade(models.Model):
    """
    Madeira (Admin, Técnico, Atleta)
    """
    # Tipos de madeira
    class Type(models.TextChoices):
        OFFENSIVE = 'OFF', _('Ofensiva')
        DEFENSIVE = 'DEF', _('Defensiva')
        ALLROUND = 'ALL', _('All-Round')
        CARBON = 'CAR', _('Carbono')
        COMPOSITE = 'COM', _('Compósita')
    
    # Classes de velocidade
    class SpeedClass(models.TextChoices):
        SLOW = 'SLOW', _('Lenta')
        MEDIUM = 'MED', _('Média')
        FAST = 'FAST', _('Rápida')
        VERY_FAST = 'VFAST', _('Muito Rápida')
    
    name = models.CharField(max_length=100, verbose_name=_('Nome'))
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blades',
        verbose_name=_('Marca')
    )
    blade_type = models.CharField(
        max_length=3,
        choices=Type.choices,
        default=Type.ALLROUND,
        verbose_name=_('Tipo')
    )
    speed_class = models.CharField(
        max_length=5,
        choices=SpeedClass.choices,
        default=SpeedClass.MEDIUM,
        verbose_name=_('Classe de Velocidade')
    )
    weight = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Peso')
    )
    layers = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Número de Camadas')
    )
    handle = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Cabo')
    )
    description = models.TextField(blank=True, verbose_name=_('Descrição'))
    is_active = models.BooleanField(default=True, verbose_name=_('Ativo'))
    created_by = models.ForeignKey(
        User,  
        on_delete=models.SET_NULL,
        null=True,
        related_name='blades_created',
        verbose_name=_('Criado por')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Madeira')
        verbose_name_plural = _('Madeiras')
        ordering = ['brand__name', 'name']
        unique_together = ['name', 'brand']
    
    def __str__(self):
        return f"{self.brand} {self.name}" if self.brand else self.name