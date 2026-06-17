from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from .forms import BladeForm, BrandForm, RubberForm
from .models import Brand, Grip, Handedness, PlayerType, Rubber, Blade

# ============================================
# VIEWS PARA TEMPLATES (INTERFACE)
# ============================================

@login_required
def equipment_list(request):
    """Lista de equipamentos (Borracha e Madeira)"""
    profile = request.user.profile
    
    # Verifica permissão
    if not (profile.is_admin() or profile.is_coach() or profile.is_athlete()):
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('dashboard')
    
    rubbers = Rubber.objects.filter(is_active=True).select_related('brand').order_by('brand__name', 'name')
    blades = Blade.objects.filter(is_active=True).select_related('brand').order_by('brand__name', 'name')
    
    context = {
        'brands': Brand.objects.filter(is_active=True).order_by('name'),
        'rubbers': rubbers,
        'blades': blades,
        'can_edit': profile.is_admin() or profile.is_coach(),
    }
    return render(request, 'equipment/equipment_list.html', context)


@login_required
def equipment_add(request):
    """Cadastro de borrachas e madeiras."""
    profile = request.user.profile

    if not (profile.is_admin() or profile.is_coach()):
        messages.error(request, 'Você não tem permissão para cadastrar equipamentos.')
        return redirect('equipment_list')

    requested_type = request.POST.get('equipment_type') or request.GET.get('type') or 'rubber'
    equipment_type = requested_type if requested_type in {'rubber', 'blade'} else 'rubber'

    form_class = RubberForm if equipment_type == 'rubber' else BladeForm
    form = form_class(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        equipment = form.save(commit=False)
        equipment.created_by = request.user
        equipment.save()
        messages.success(
            request,
            'Borracha cadastrada com sucesso!' if equipment_type == 'rubber' else 'Madeira cadastrada com sucesso!'
        )
        redirect_target = 'rubbers' if equipment_type == 'rubber' else 'blades'
        return redirect(f"{reverse('equipment_list')}#{redirect_target}")

    context = {
        'equipment_type': equipment_type,
        'form': form,
        'title': 'Nova Borracha' if equipment_type == 'rubber' else 'Nova Madeira',
        'icon': 'fa-circle' if equipment_type == 'rubber' else 'fa-ping-pong',
        'button_class': 'btn-primary' if equipment_type == 'rubber' else 'btn-success',
        'submit_label': 'Salvar Cadastro',
    }
    return render(request, 'equipment/equipment_add.html', context)


@login_required
def equipment_edit(request, equipment_type, pk):
    """Edição de borrachas e madeiras."""
    profile = request.user.profile

    if not (profile.is_admin() or profile.is_coach()):
        messages.error(request, 'Você não tem permissão para editar equipamentos.')
        return redirect('equipment_list')

    if equipment_type == 'rubber':
        instance = get_object_or_404(Rubber, pk=pk)
        form_class = RubberForm
        title = 'Editar Borracha'
        icon = 'fa-circle'
        button_class = 'btn-primary'
        redirect_target = 'rubbers'
    elif equipment_type == 'blade':
        instance = get_object_or_404(Blade, pk=pk)
        form_class = BladeForm
        title = 'Editar Madeira'
        icon = 'fa-ping-pong'
        button_class = 'btn-success'
        redirect_target = 'blades'
    else:
        messages.error(request, 'Tipo de equipamento inválido.')
        return redirect('equipment_list')

    form = form_class(request.POST or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            'Borracha atualizada com sucesso!' if equipment_type == 'rubber' else 'Madeira atualizada com sucesso!'
        )
        return redirect(f"{reverse('equipment_list')}#{redirect_target}")

    context = {
        'equipment_type': equipment_type,
        'form': form,
        'title': title,
        'icon': icon,
        'button_class': button_class,
        'submit_label': 'Salvar Alterações',
    }
    return render(request, 'equipment/equipment_add.html', context)


@login_required
def brand_add(request):
    """Cadastro de marcas de equipamentos."""
    profile = request.user.profile

    if not (profile.is_admin() or profile.is_coach()):
        messages.error(request, 'Você não tem permissão para cadastrar marcas.')
        return redirect('equipment_list')

    form = BrandForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        brand = form.save()
        messages.success(request, f'Marca {brand.name} cadastrada com sucesso!')
        return redirect('equipment_list')

    return render(request, 'equipment/brand_add.html', {
        'form': form,
        'title': 'Nova Marca',
        'submit_label': 'Salvar Marca',
    })


@login_required
def brand_edit(request, pk):
    """Edição de marcas de equipamentos."""
    profile = request.user.profile

    if not (profile.is_admin() or profile.is_coach()):
        messages.error(request, 'Você não tem permissão para editar marcas.')
        return redirect('equipment_list')

    brand = get_object_or_404(Brand, pk=pk)
    form = BrandForm(request.POST or None, instance=brand)

    if request.method == 'POST' and form.is_valid():
        brand = form.save()
        messages.success(request, f'Marca {brand.name} atualizada com sucesso!')
        return redirect(f"{reverse('equipment_list')}#brands")

    return render(request, 'equipment/brand_add.html', {
        'form': form,
        'title': 'Editar Marca',
        'submit_label': 'Salvar Alterações',
    })

@login_required
def grip_list(request):
    """Lista de empunhaduras (apenas Admin)"""
    if not request.user.profile.is_admin():
        messages.error(request, 'Apenas administradores podem acessar esta página.')
        return redirect('dashboard')
    
    grips = Grip.objects.filter(is_active=True)
    context = {'grips': grips}
    return render(request, 'equipment/grip_list.html', context)

@login_required
def player_type_list(request):
    """Lista de tipos de atleta (apenas Admin)"""
    if not request.user.profile.is_admin():
        messages.error(request, 'Apenas administradores podem acessar esta página.')
        return redirect('dashboard')
    
    types = PlayerType.objects.filter(is_active=True)
    context = {'types': types}
    return render(request, 'equipment/player_type_list.html', context)

# ============================================
# VIEWS PARA API (REST FRAMEWORK)
# ============================================

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import (
    BrandSerializer, GripSerializer, HandednessSerializer, PlayerTypeSerializer,
    RubberSerializer, BladeSerializer
)

User = get_user_model()

class IsAdminOrReadOnly(permissions.BasePermission):
    """Permissão: Admin pode tudo, outros só leitura"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.profile.is_admin()

class IsAdminOrCoachOrAthlete(permissions.BasePermission):
    """Permissão: Admin, Técnico e Atleta podem tudo"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile = request.user.profile
        return profile.is_admin() or profile.is_coach() or profile.is_athlete()

# ============================================
# APENAS ADMINISTRADORES
# ============================================

class BrandViewSet(viewsets.ModelViewSet):
    """ViewSet para Marcas de Equipamentos"""
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrCoachOrAthlete]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

class GripViewSet(viewsets.ModelViewSet):
    """ViewSet para Empunhaduras (apenas Admin)"""
    queryset = Grip.objects.filter(is_active=True)
    serializer_class = GripSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

class HandednessViewSet(viewsets.ModelViewSet):
    """ViewSet para Mãos Dominantes (apenas Admin)"""
    queryset = Handedness.objects.filter(is_active=True)
    serializer_class = HandednessSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

class PlayerTypeViewSet(viewsets.ModelViewSet):
    """ViewSet para Tipos de Atleta (apenas Admin)"""
    queryset = PlayerType.objects.filter(is_active=True)
    serializer_class = PlayerTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

# ============================================
# ADMIN, TÉCNICOS E ATLETAS
# ============================================

class RubberViewSet(viewsets.ModelViewSet):
    """ViewSet para Borrachas (Admin, Técnico, Atleta)"""
    queryset = Rubber.objects.filter(is_active=True).select_related('brand')
    serializer_class = RubberSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrCoachOrAthlete]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        category = self.request.query_params.get('category', None)
        rubber_type = self.request.query_params.get('rubber_type', None)
        search = self.request.query_params.get('search', None)
        
        if category:
            queryset = queryset.filter(category=category)
        if rubber_type:
            queryset = queryset.filter(rubber_type=rubber_type)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(brand__name__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Retorna as categorias disponíveis"""
        categories = [{'value': c[0], 'label': c[1]} for c in Rubber.Category.choices]
        return Response(categories)

class BladeViewSet(viewsets.ModelViewSet):
    """ViewSet para Madeiras (Admin, Técnico, Atleta)"""
    queryset = Blade.objects.filter(is_active=True).select_related('brand')
    serializer_class = BladeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrCoachOrAthlete]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        blade_type = self.request.query_params.get('blade_type', None)
        speed_class = self.request.query_params.get('speed_class', None)
        search = self.request.query_params.get('search', None)
        
        if blade_type:
            queryset = queryset.filter(blade_type=blade_type)
        if speed_class:
            queryset = queryset.filter(speed_class=speed_class)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(brand__name__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Retorna os tipos disponíveis"""
        types = [{'value': t[0], 'label': t[1]} for t in Blade.Type.choices]
        return Response(types)
    
    @action(detail=False, methods=['get'])
    def speed_classes(self, request):
        """Retorna as classes de velocidade disponíveis"""
        speed_classes = [{'value': s[0], 'label': s[1]} for s in Blade.SpeedClass.choices]
        return Response(speed_classes)