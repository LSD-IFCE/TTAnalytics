from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Club

User = get_user_model()

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ('name', 'acronym', 'city', 'state', 'get_coaches_count', 'is_active')
    list_filter = ('is_active', 'city', 'state')
    search_fields = ('name', 'acronym', 'city', 'email')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'acronym', 'logo')
        }),
        ('Endereço', {
            'fields': ('address', 'city', 'state')
        }),
        ('Contato', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Controle', {
            'fields': ('is_active', 'created_by')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_coaches_count(self, obj):
        return obj.get_coaches_count()
    get_coaches_count.short_description = 'Técnicos'
    
    def get_athletes_count(self, obj):
        return obj.get_athletes_count()
    get_athletes_count.short_description = 'Atletas'