from django.contrib.auth.models import User as AuthUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


def build_profile_defaults(user):
    """Monta defaults seguros para usuários legados sem perfil."""
    full_name = ' '.join(part for part in [user.first_name, user.last_name] if part).strip()

    if user.is_staff or user.is_superuser:
        user_type = Profile.UserType.ADMIN
        approval_status = Profile.ApprovalStatus.APPROVED
    else:
        user_type = Profile.UserType.ATHLETE
        approval_status = Profile.ApprovalStatus.APPROVED if user.is_active else Profile.ApprovalStatus.PENDING

    return {
        'full_name': full_name or user.username,
        'user_type': user_type,
        'approval_status': approval_status,
    }


def ensure_profile_for_user(user):
    """Garante que o usuário tenha um perfil associado."""
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults=build_profile_defaults(user),
    )
    return profile

class Profile(models.Model):
    """
    Perfil do usuário com campos adicionais
    """
    
    # Tipos de usuário
    class UserType(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrador')
        COACH = 'COACH', _('Técnico')
        ATHLETE = 'ATHLETE', _('Atleta')
        ANALYST = 'ANALYST', _('Analista')
    
    # Status de aprovação
    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', _('Aguardando Aprovação')
        APPROVED = 'APPROVED', _('Aprovado')
        REJECTED = 'REJECTED', _('Rejeitado')
    
    user = models.OneToOneField(
        AuthUser,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('Usuário')
    )
    
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.ATHLETE,
        verbose_name=_('Tipo de Usuário')
    )
    
    full_name = models.CharField(
        max_length=255,
        verbose_name=_('Nome Completo')
    )
    
    birth_date = models.DateField(
        null=True,  
        blank=True,          
        verbose_name=_('Data de Nascimento')
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Telefone')
    )
    
    photo = models.ImageField(
        upload_to='profiles/photos/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_('Foto')
    )

    dominant_hand = models.ForeignKey(
        'equipment.Handedness',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles',
        verbose_name=_('Mão Dominante')
    )

    player_type = models.ForeignKey(
        'equipment.PlayerType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles',
        verbose_name=_('Tipo')
    )

    blade = models.ForeignKey(
        'equipment.Blade',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles_using_blade',
        verbose_name=_('Madeira')
    )

    rubber_1 = models.ForeignKey(
        'equipment.Rubber',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles_using_rubber_1',
        verbose_name=_('Borracha 1')
    )

    rubber_2 = models.ForeignKey(
        'equipment.Rubber',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles_using_rubber_2',
        verbose_name=_('Borracha 2')
    )

    grip = models.ForeignKey(
        'equipment.Grip',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles',
        verbose_name=_('Empunhadura')
    )
    
    # ⭐ Clube do usuário (pode ser None para Admin e Analista)
    club = models.ForeignKey(
        'clubs.Club',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name=_('Clube')
    )
    
    # ⭐ Status de aprovação
    approval_status = models.CharField(
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        verbose_name=_('Status da Aprovação')
    )
    
    reviewed_by = models.ForeignKey(
        AuthUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_profiles',
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
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Criado em')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Atualizado em')
    )
    
    class Meta:
        verbose_name = _('Perfil')
        verbose_name_plural = _('Perfis')
        db_table = 'users_profile'
    
    def __str__(self):
        status_emoji = {
            'PENDING': '⏳',
            'APPROVED': '✅',
            'REJECTED': '❌'
        }.get(self.approval_status, '❓')
        return f"{status_emoji} {self.full_name} ({self.get_user_type_display()})"
    
    def clean(self):
        """Validações customizadas"""
        # Técnico precisa ter clube
        if self.user_type in [self.UserType.COACH, self.UserType.ATHLETE] and not self.club:
            raise ValidationError({
                'club': f'{self.get_user_type_display()} deve estar associado a um clube.'
            })
        
        # Admin e Analista não precisam de clube
        if self.user_type in [self.UserType.ADMIN, self.UserType.ANALYST] and self.club:
            # Não é obrigatório, mas pode ter se quiser
            pass
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    # Métodos de verificação
    def is_admin(self):
        return self.user_type == self.UserType.ADMIN
    
    def is_coach(self):
        return self.user_type == self.UserType.COACH
    
    def is_athlete(self):
        return self.user_type == self.UserType.ATHLETE
    
    def is_analyst(self):
        return self.user_type == self.UserType.ANALYST
    
    def is_approved(self):
        return self.approval_status == self.ApprovalStatus.APPROVED
    
    def is_pending(self):
        return self.approval_status == self.ApprovalStatus.PENDING
    
    def is_rejected(self):
        return self.approval_status == self.ApprovalStatus.REJECTED
    
    def can_approve_user(self, target_profile):
        """Verifica se o usuário atual pode aprovar outro usuário"""
        
        # Admin aprova qualquer um
        if self.is_admin():
            return True
        
        # Técnico aprova apenas atletas do mesmo clube
        if self.is_coach():
            if target_profile.is_athlete():
                return self.club == target_profile.club
            # Técnico não pode aprovar outro técnico
            return False
        
        return False
    
    def can_view_approval_status(self, target_profile):
        """Verifica se o usuário pode ver o status de aprovação de outro"""
        if self.is_admin():
            return True
        
        if self.is_coach():
            return self.club == target_profile.club
        
        if self.user == target_profile.user:
            return True
        
        return False
    
    def approve(self, reviewer):
        """Aprova o cadastro"""
        if not reviewer.profile.can_approve_user(self):
            raise PermissionError(
                f'{reviewer.profile.full_name} não tem permissão para aprovar {self.full_name}'
            )
        
        self.approval_status = self.ApprovalStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.user.is_active = True
        self.user.save()
        self.save()
    
    def reject(self, reviewer, reason):
        """Rejeita o cadastro"""
        if not reviewer.profile.can_approve_user(self):
            raise PermissionError(
                f'{reviewer.profile.full_name} não tem permissão para rejeitar {self.full_name}'
            )
        
        self.approval_status = self.ApprovalStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.user.is_active = False
        self.user.save()
        self.save()
    
    def get_status_display_with_icon(self):
        """Retorna status com ícone para exibição"""
        status_icons = {
            'PENDING': '⏳ Pendente',
            'APPROVED': '✅ Aprovado',
            'REJECTED': '❌ Rejeitado'
        }
        return status_icons.get(self.approval_status, '❓ Desconhecido')
    
    def get_review_info(self):
        """Retorna informações sobre quem revisou e quando"""
        if not self.reviewed_by:
            return None
        
        return {
            'reviewer_name': self.reviewed_by.profile.full_name,
            'reviewer_type': self.reviewed_by.profile.get_user_type_display(),
            'reviewed_at': self.reviewed_at,
            'rejection_reason': self.rejection_reason if self.is_rejected() else None
        }
    
    def get_avatar_url(self):
        """Retorna a URL da foto do usuário ou uma imagem genérica"""
        if self.photo and hasattr(self.photo, 'url'):
            return self.photo.url
        return '/static/images/default-avatar.png'
    
    def get_club_logo_url(self):
        """Retorna a URL da logo do clube ou uma imagem genérica"""
        if self.club and self.club.logo and hasattr(self.club.logo, 'url'):
            return self.club.logo.url
        return '/static/images/default-club.png'
    
    def get_club_initial(self):
        """Retorna as iniciais do clube para fallback"""
        if self.club:
            if self.club.acronym:
                return self.club.acronym[:2].upper()
            return self.club.name[:2].upper()
        return ''
    
    def get_user_badge(self):
        """Retorna o badge do tipo de usuário"""
        badges = {
            'ADMIN': {'icon': 'fas fa-user-shield', 'color': 'danger', 'label': 'Admin'},
            'COACH': {'icon': 'fas fa-table-tennis-paddle-ball', 'color': 'success', 'label': 'Técnico'},
            'ATHLETE': {'icon': 'fas fa-bullseye', 'color': 'primary', 'label': 'Atleta'},
            'ANALYST': {'icon': 'fas fa-chart-line', 'color': 'warning', 'label': 'Analista'},
        }
        return badges.get(self.user_type, {'icon': 'fas fa-user', 'color': 'secondary', 'label': 'Usuário'})