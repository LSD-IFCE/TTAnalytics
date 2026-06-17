from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

User = get_user_model()

class Club(models.Model):
    """
    Clube de tênis de mesa
    """
    
    # Status de aprovação do clube
    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', _('Aguardando Aprovação')
        APPROVED = 'APPROVED', _('Aprovado')
        REJECTED = 'REJECTED', _('Rejeitado')
    
    name = models.CharField(
        max_length=200, 
        unique=True, 
        verbose_name=_('Nome do Clube')
    )
    acronym = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name=_('Sigla')
    )
    
    # Endereço
    address = models.TextField(blank=True, verbose_name=_('Endereço'))
    city = models.CharField(max_length=100, blank=True, verbose_name=_('Cidade'))
    state = models.CharField(max_length=2, blank=True, verbose_name=_('Estado'))
    
    # Contato
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('Telefone'))
    email = models.EmailField(blank=True, verbose_name=_('E-mail'))
    website = models.URLField(blank=True, verbose_name=_('Site'))
    
    # ⭐ Status de aprovação do clube
    approval_status = models.CharField(
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        verbose_name=_('Status da Aprovação')
    )
    
    # ⭐ Quem aprovou/rejeitou o clube
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_clubs',
        verbose_name=_('Revisado por')
    )
    
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Revisado em')
    )
    
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Motivo da rejeição')
    )
    
    # ⭐ Técnico que criou/solicitou o clube
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_clubs',
        limit_choices_to={'profile__user_type': 'COACH'},
        verbose_name=_('Solicitado por')
    )
    
    # Metadados
    logo = models.ImageField(
        upload_to='clubs/logos/%Y/%m/', 
        blank=True, 
        null=True,
        verbose_name=_('Logo')
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_('Ativo')
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='clubs_created',
        verbose_name=_('Criado por')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Clube')
        verbose_name_plural = _('Clubes')
        ordering = ['name']
    
    def __str__(self):
        status_emoji = {
            'PENDING': '⏳',
            'APPROVED': '✅',
            'REJECTED': '❌'
        }.get(self.approval_status, '❓')
        return f"{status_emoji} {self.name}"
    
    def is_approved(self):
        return self.approval_status == self.ApprovalStatus.APPROVED
    
    def is_pending(self):
        return self.approval_status == self.ApprovalStatus.PENDING
    
    def is_rejected(self):
        return self.approval_status == self.ApprovalStatus.REJECTED
    
    def approve(self, reviewer):
        """Aprova o clube"""
        self.approval_status = self.ApprovalStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.is_active = True
        self.save()
    
    def reject(self, reviewer, reason):
        """Rejeita o clube"""
        self.approval_status = self.ApprovalStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.is_active = False
        self.save()
    
    def get_status_display_with_icon(self):
        """Retorna status com ícone para exibição"""
        status_icons = {
            'PENDING': '⏳ Pendente',
            'APPROVED': '✅ Aprovado',
            'REJECTED': '❌ Rejeitado'
        }
        return status_icons.get(self.approval_status, '❓ Desconhecido')
    
    def get_coaches(self):
        """Retorna todos os técnicos do clube"""
        return User.objects.filter(
            profile__user_type='COACH',
            profile__club=self
        )
    
    def get_coaches_count(self):
        """Retorna o número de técnicos do clube"""
        return self.get_coaches().count()
    
    def get_athletes(self):
        """Retorna todos os atletas do clube"""
        return User.objects.filter(
            profile__user_type='ATHLETE',
            profile__club=self
        )
    
    def get_athletes_count(self):
        """Retorna o número de atletas do clube"""
        return self.get_athletes().count()