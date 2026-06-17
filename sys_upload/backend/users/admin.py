from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import Profile

class ProfileInline(admin.StackedInline):
    """Inclui o perfil dentro do admin de usuário"""
    model = Profile
    can_delete = False
    verbose_name_plural = 'Perfil'
    fk_name = 'user'
    
    fields = (
        'user_type',
        'full_name',
        'birth_date',
        'phone',
        'photo',
        # 'club',
    )

class CustomUserAdmin(UserAdmin):
    """Admin personalizado com perfil incluso"""
    
    inlines = (ProfileInline,)
    
    list_display = (
        'username',
        'email',
        'get_full_name',
        'get_user_type',
        'is_active',
        'is_staff',
        'date_joined'
    )
    
    list_filter = (
        'profile__user_type',
        'is_active',
        'is_staff',
        'is_superuser',
    )
    
    search_fields = (
        'username',
        'email',
        'profile__full_name',
    )
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Informações Pessoais'), {
            'fields': (
                'first_name',
                'last_name',
                'email'
            )
        }),
        (_('Permissões'), {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            ),
        }),
        (_('Datas Importantes'), {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    def get_full_name(self, obj):
        """Retorna o nome completo do perfil"""
        if hasattr(obj, 'profile'):
            return obj.profile.full_name
        return obj.get_full_name()
    get_full_name.short_description = 'Nome Completo'
    
    def get_user_type(self, obj):
        """Retorna o tipo de usuário"""
        if hasattr(obj, 'profile'):
            return obj.profile.get_user_type_display()
        return '-'
    get_user_type.short_description = 'Tipo de Usuário'
    get_user_type.admin_order_field = 'profile__user_type'

# Re-registra o User admin com a customização
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Registra o Profile separadamente
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'user_type', 'phone')
    list_filter = ('user_type',)
    search_fields = ('full_name', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')