from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import Brand, Grip, Handedness, PlayerType, Rubber, Blade

User = get_user_model()

# ============================================
# ADMIN APENAS PARA ADMINISTRADORES
# ============================================

@admin.register(Grip)
class GripAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {'fields': ('name', 'description')}),
        (_('Controle'), {'fields': ('is_active',)}),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.profile.is_admin():
            return qs
        return qs.none()
    
    def has_module_permission(self, request):
        return request.user.profile.is_admin()
    
    def has_add_permission(self, request):
        return request.user.profile.is_admin()
    
    def has_change_permission(self, request, obj=None):
        return request.user.profile.is_admin()
    
    def has_delete_permission(self, request, obj=None):
        return request.user.profile.is_admin()

@admin.register(Handedness)
class HandednessAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    
    def has_module_permission(self, request):
        return request.user.profile.is_admin()
    
    def has_add_permission(self, request):
        return request.user.profile.is_admin()
    
    def has_change_permission(self, request, obj=None):
        return request.user.profile.is_admin()
    
    def has_delete_permission(self, request, obj=None):
        return request.user.profile.is_admin()

@admin.register(PlayerType)
class PlayerTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    
    def has_module_permission(self, request):
        return request.user.profile.is_admin()
    
    def has_add_permission(self, request):
        return request.user.profile.is_admin()
    
    def has_change_permission(self, request, obj=None):
        return request.user.profile.is_admin()
    
    def has_delete_permission(self, request, obj=None):
        return request.user.profile.is_admin()


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)

    def has_module_permission(self, request):
        return request.user.profile.is_admin()

    def has_add_permission(self, request):
        return request.user.profile.is_admin()

    def has_change_permission(self, request, obj=None):
        return request.user.profile.is_admin()

    def has_delete_permission(self, request, obj=None):
        return request.user.profile.is_admin()

# ============================================
# ADMIN PARA ADMIN, TÉCNICOS E ATLETAS
# ============================================

@admin.register(Rubber)
class RubberAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'rubber_type', 'is_active')
    list_filter = ('brand', 'category', 'rubber_type', 'is_active')
    search_fields = ('name', 'brand__name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'brand', 'category', 'rubber_type')
        }),
        (_('Detalhes'), {
            'fields': ('thickness', 'color', 'description')
        }),
        (_('Controle'), {
            'fields': ('is_active', 'created_by')
        }),
    )
    readonly_fields = ('created_by',)
    
    def save_model(self, request, obj, form, change):
        if not change:  # Novo objeto
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_module_permission(self, request):
        profile = request.user.profile
        return profile.is_admin() or profile.is_coach() or profile.is_athlete()
    
    def has_add_permission(self, request):
        profile = request.user.profile
        return profile.is_admin() or profile.is_coach() or profile.is_athlete()
    
    def has_change_permission(self, request, obj=None):
        profile = request.user.profile
        if profile.is_admin():
            return True
        if obj and obj.created_by == request.user:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        profile = request.user.profile
        if profile.is_admin():
            return True
        if obj and obj.created_by == request.user:
            return True
        return False

@admin.register(Blade)
class BladeAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'blade_type', 'speed_class', 'is_active')
    list_filter = ('brand', 'blade_type', 'speed_class', 'is_active')
    search_fields = ('name', 'brand__name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'brand', 'blade_type', 'speed_class')
        }),
        (_('Detalhes'), {
            'fields': ('weight', 'layers', 'handle', 'description')
        }),
        (_('Controle'), {
            'fields': ('is_active', 'created_by')
        }),
    )
    readonly_fields = ('created_by',)
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_module_permission(self, request):
        profile = request.user.profile
        return profile.is_admin() or profile.is_coach() or profile.is_athlete()
    
    def has_add_permission(self, request):
        profile = request.user.profile
        return profile.is_admin() or profile.is_coach() or profile.is_athlete()
    
    def has_change_permission(self, request, obj=None):
        profile = request.user.profile
        if profile.is_admin():
            return True
        if obj and obj.created_by == request.user:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        profile = request.user.profile
        if profile.is_admin():
            return True
        if obj and obj.created_by == request.user:
            return True
        return False