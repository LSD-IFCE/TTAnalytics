from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from .forms import ManagedClubCreateForm, ManagedUserCreateForm
from equipment.models import Blade, Grip, Handedness, PlayerType, Rubber
from users.models import Profile, ensure_profile_for_user
from clubs.models import Club


def get_profile_equipment_context():
    return {
        'handedness_options': Handedness.objects.filter(is_active=True).order_by('name'),
        'player_type_options': PlayerType.objects.filter(is_active=True).order_by('name'),
        'blade_options': Blade.objects.filter(is_active=True).select_related('brand').order_by('brand__name', 'name'),
        'rubber_options': Rubber.objects.filter(is_active=True).select_related('brand').order_by('brand__name', 'name'),
        'grip_options': Grip.objects.filter(is_active=True).order_by('name'),
    }


def parse_optional_fk(model, raw_value):
    if not raw_value:
        return None
    try:
        return model.objects.get(pk=raw_value)
    except model.DoesNotExist:
        return None

def home(request):
    """Página inicial do sistema"""
    if request.user.is_authenticated:
        ensure_profile_for_user(request.user)
    return render(request, 'core/home.html')

def login_view(request):
    """Página de login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            ensure_profile_for_user(user)
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    
    return render(request, 'core/login.html')

def register_view(request):
    """Página de registro de usuário"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    def render_register_with_context():
        context = {
            'clubs': clubs,
            'user_types': Profile.UserType.choices,
            'form_data': request.POST if request.method == 'POST' else {},
        }
        context.update(get_profile_equipment_context())
        return render(request, 'core/register.html', context)
    
    # Busca clubes existentes para o select
    clubs = Club.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        birth_date = request.POST.get('birth_date')
        photo = request.FILES.get('photo')
        user_type = request.POST.get('user_type', 'ATHLETE')
        club_id = request.POST.get('club_id')  # ⭐ Clube selecionado
        dominant_hand = parse_optional_fk(Handedness, request.POST.get('dominant_hand'))
        player_type = parse_optional_fk(PlayerType, request.POST.get('player_type'))
        blade = parse_optional_fk(Blade, request.POST.get('blade'))
        rubber_1 = parse_optional_fk(Rubber, request.POST.get('rubber_1'))
        rubber_2 = parse_optional_fk(Rubber, request.POST.get('rubber_2'))
        grip = parse_optional_fk(Grip, request.POST.get('grip'))
        create_club = request.POST.get('create_club') == '1'
        club_full_name = request.POST.get('club_full_name', '').strip()
        club_acronym = request.POST.get('club_acronym', '').strip()
        club_city = request.POST.get('club_city', '').strip()
        club_state = request.POST.get('club_state', '').strip().upper()
        club_phone = request.POST.get('club_phone', '').strip()
        club_email = request.POST.get('club_email', '').strip()
        club_logo = request.FILES.get('club_logo')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validações
        if password1 != password2:
            messages.error(request, 'As senhas não coincidem.')
            return render_register_with_context()
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Este nome de usuário já está em uso.')
            return render_register_with_context()
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Este e-mail já está cadastrado.')
            return render_register_with_context()
        
        # ⭐ Atleta deve escolher clube existente
        if user_type == 'ATHLETE' and not club_id:
            messages.error(request, f'{dict(Profile.UserType.choices).get(user_type)} deve estar associado a um clube.')
            return render_register_with_context()

        # ⭐ Técnico pode escolher clube existente ou cadastrar um novo
        if user_type == 'COACH':
            if create_club and not club_full_name:
                messages.error(request, 'Informe o nome do clube para cadastrar um novo clube.')
                return render_register_with_context()

            if not create_club and not club_id:
                messages.error(request, 'Selecione um clube existente ou cadastre um novo clube.')
                return render_register_with_context()
        
        # Busca o clube existente
        club = None
        if club_id and (user_type != 'COACH' or not create_club):
            try:
                club = Club.objects.get(id=club_id, is_active=True)
            except Club.DoesNotExist:
                messages.error(request, 'Clube não encontrado.')
                return render_register_with_context()

        try:
            with transaction.atomic():
                # Cria o usuário INATIVO
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                    first_name=full_name.split()[0] if full_name else '',
                    last_name=' '.join(full_name.split()[1:]) if full_name else '',
                    is_active=False
                )

                if user_type == 'COACH' and create_club:
                    club = Club.objects.create(
                        name=club_full_name,
                        acronym=club_acronym,
                        city=club_city,
                        state=club_state,
                        phone=club_phone,
                        email=club_email,
                        logo=club_logo,
                        approval_status=Club.ApprovalStatus.PENDING,
                        is_active=False,
                        created_by=user,
                        requested_by=user,
                    )

                # ⭐ Cria o perfil com clube e pendente
                Profile.objects.create(
                    user=user,
                    full_name=full_name,
                    birth_date=birth_date if birth_date else None,
                    photo=photo,
                    user_type=user_type,
                    club=club,
                    dominant_hand=dominant_hand,
                    player_type=player_type,
                    blade=blade,
                    rubber_1=rubber_1,
                    rubber_2=rubber_2,
                    grip=grip,
                    approval_status=Profile.ApprovalStatus.PENDING
                )
        except Exception as exc:
            messages.error(request, f'Não foi possível concluir o cadastro: {exc}')
            return render_register_with_context()
        
        # Mensagem específica para técnico
        if user_type == 'COACH':
            messages.success(
                request, 
                'Conta de técnico criada com sucesso! O clube será validado junto com seu cadastro. Aguarde a aprovação de um administrador.'
            )
        else:
            messages.success(
                request, 
                'Conta criada com sucesso! Aguarde a aprovação de um administrador ou técnico.'
            )
        
        return redirect('login')
    
    context = {
        'clubs': clubs,
        'user_types': Profile.UserType.choices,
        'form_data': {},
    }
    context.update(get_profile_equipment_context())
    return render(request, 'core/register.html', context)


@login_required
def managed_user_create(request, user_type):
    """Cadastro interno de técnicos e atletas."""
    profile = ensure_profile_for_user(request.user)
    allowed_user_types = {
        'coach': Profile.UserType.COACH,
        'athlete': Profile.UserType.ATHLETE,
    }

    if user_type not in allowed_user_types:
        messages.error(request, 'Tipo de usuário inválido.')
        return redirect('dashboard')

    if not (profile.is_admin() or profile.is_coach()):
        messages.error(request, 'Você não tem permissão para cadastrar usuários.')
        return redirect('dashboard')

    if profile.is_coach() and user_type != 'athlete':
        messages.error(request, 'Técnicos só podem cadastrar atletas.')
        return redirect('dashboard')

    fixed_club = profile.club if profile.is_coach() else None
    if profile.is_coach() and not fixed_club:
        messages.error(request, 'Seu perfil precisa estar vinculado a um clube para cadastrar atletas.')
        return redirect('dashboard')

    lock_club = profile.is_coach() and user_type == 'athlete'
    form = ManagedUserCreateForm(request.POST or None, request.FILES or None, lock_club=lock_club, fixed_club=fixed_club)

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        email = form.cleaned_data['email']
        if User.objects.filter(username=username).exists():
            form.add_error('username', 'Este nome de usuário já está em uso.')
        if User.objects.filter(email=email).exists():
            form.add_error('email', 'Este e-mail já está cadastrado.')

        selected_club = fixed_club if lock_club else form.cleaned_data.get('club')
        if allowed_user_types[user_type] in {Profile.UserType.COACH, Profile.UserType.ATHLETE} and not selected_club:
            form.add_error('club', 'Selecione um clube para este cadastro.')

        if not form.errors:
            full_name = form.cleaned_data['full_name']
            user = User.objects.create_user(
                username=username,
                email=email,
                password=form.cleaned_data['password1'],
                first_name=full_name.split()[0] if full_name else '',
                last_name=' '.join(full_name.split()[1:]) if full_name else '',
                is_active=True,
            )
            Profile.objects.create(
                user=user,
                full_name=full_name,
                birth_date=form.cleaned_data.get('birth_date'),
                photo=form.cleaned_data.get('photo'),
                user_type=allowed_user_types[user_type],
                club=selected_club,
                dominant_hand=form.cleaned_data.get('dominant_hand'),
                player_type=form.cleaned_data.get('player_type'),
                blade=form.cleaned_data.get('blade'),
                rubber_1=form.cleaned_data.get('rubber_1'),
                rubber_2=form.cleaned_data.get('rubber_2'),
                grip=form.cleaned_data.get('grip'),
                approval_status=Profile.ApprovalStatus.APPROVED,
                reviewed_by=request.user,
                reviewed_at=timezone.now(),
            )
            messages.success(
                request,
                'Técnico cadastrado com sucesso!' if user_type == 'coach' else 'Atleta cadastrado com sucesso!'
            )
            return redirect('dashboard')

    context = {
        'form': form,
        'title': 'Cadastrar Técnico' if user_type == 'coach' else 'Cadastrar Atleta',
        'submit_label': 'Cadastrar Técnico' if user_type == 'coach' else 'Cadastrar Atleta',
        'user_type_label': 'Técnico' if user_type == 'coach' else 'Atleta',
        'show_club_selector': not lock_club,
        'fixed_club': fixed_club,
    }
    return render(request, 'core/managed_user_create.html', context)


@login_required
def managed_club_create(request):
    """Cadastro interno de clubes para administradores."""
    profile = ensure_profile_for_user(request.user)
    if not profile.is_admin():
        messages.error(request, 'Apenas administradores podem cadastrar clubes.')
        return redirect('dashboard')

    form = ManagedClubCreateForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        club = form.save(commit=False)
        club.created_by = request.user
        club.approval_status = Club.ApprovalStatus.APPROVED
        club.reviewed_by = request.user
        club.reviewed_at = timezone.now()
        club.is_active = True
        club.save()
        messages.success(request, f'Clube {club.name} cadastrado com sucesso!')
        return redirect('dashboard')

    return render(request, 'core/managed_club_create.html', {
        'form': form,
        'title': 'Cadastrar Clube',
        'submit_label': 'Cadastrar Clube',
    })

@login_required
def dashboard(request):
    """Dashboard do usuário"""
    profile = ensure_profile_for_user(request.user)
    
    # Dados básicos
    context = {
        'total_videos': 0,
        'total_athletes': 0,
        'total_matches': 0,
        'total_metrics': 0,
    }
    
    # ⭐ Pendências para Admin
    if profile.is_admin():
        pending_users = Profile.objects.filter(
            approval_status='PENDING'
        ).count()
        pending_clubs = Club.objects.filter(
            approval_status='PENDING'
        ).count()
        context['pending_users'] = pending_users
        context['pending_clubs'] = pending_clubs
        context['total_pending'] = pending_users + pending_clubs
    
    # ⭐ Pendências para Técnico
    elif profile.is_coach():
        if profile.club:
            pending_athletes = Profile.objects.filter(
                approval_status='PENDING',
                user_type='ATHLETE',
                club=profile.club
            ).count()
            context['pending_athletes'] = pending_athletes
        else:
            context['no_club'] = True
    
    # ⭐ Se for atleta, mostra status do cadastro
    elif profile.is_athlete():
        context['is_approved'] = profile.is_approved()
        context['is_pending'] = profile.is_pending()
    
    return render(request, 'core/dashboard.html', context)

@login_required
def logout_view(request):
    """Logout do usuário"""
    logout(request)
    messages.info(request, 'Você saiu do sistema.')
    return redirect('home')

@login_required
def pending_approvals(request):
    """Lista de contas pendentes de aprovação"""
    profile = ensure_profile_for_user(request.user)
    
    # Filtra perfis pendentes baseado na permissão do usuário
    if profile.is_admin():
        # Admin vê todos os pendentes
        pending_profiles = Profile.objects.filter(
            approval_status='PENDING'
        ).select_related('user', 'club')
    
    elif profile.is_coach():
        # Técnico vê apenas atletas pendentes do seu clube
        if profile.club:
            pending_profiles = Profile.objects.filter(
                approval_status='PENDING',
                user_type='ATHLETE',
                club=profile.club
            ).select_related('user', 'club')
        else:
            pending_profiles = Profile.objects.none()
            messages.warning(request, 'Você não está associado a nenhum clube.')
    
    else:
        # Outros usuários não veem
        pending_profiles = Profile.objects.none()
        messages.warning(request, 'Você não tem permissão para ver aprovações pendentes.')
    
    context = {
        'pending_profiles': pending_profiles,
        'total_pending': pending_profiles.count(),
        'is_admin': profile.is_admin(),
        'is_coach': profile.is_coach(),
    }
    return render(request, 'core/pending_approvals.html', context)

@login_required
def pending_clubs(request):
    """Lista de clubes pendentes de aprovação"""
    profile = ensure_profile_for_user(request.user)

    if not profile.is_admin():
        messages.warning(request, 'Você não tem permissão para ver clubes pendentes.')
        return redirect('dashboard')

    pending_clubs = Club.objects.filter(
        approval_status='PENDING'
    ).select_related('requested_by', 'reviewed_by')

    context = {
        'pending_clubs': pending_clubs,
        'total_pending': pending_clubs.count(),
    }
    return render(request, 'core/pending_clubs.html', context)

@login_required
def approve_user(request, profile_id):
    """Aprova uma conta de usuário"""
    profile = ensure_profile_for_user(request.user)
    target_profile = get_object_or_404(Profile, id=profile_id)
    
    # Verifica permissão
    if not profile.can_approve_user(target_profile):
        messages.error(request, 'Você não tem permissão para aprovar este usuário.')
        return redirect('pending_approvals')
    
    # Se já foi aprovado
    if target_profile.is_approved():
        messages.warning(request, f'{target_profile.full_name} já foi aprovado.')
        return redirect('pending_approvals')
    
    if request.method == 'POST':
        try:
            target_profile.approve(request.user)
            messages.success(request, f'{target_profile.full_name} foi aprovado com sucesso!')
        except PermissionError as e:
            messages.error(request, str(e))
        return redirect('pending_approvals')
    
    context = {
        'target_profile': target_profile,
        'action': 'approve'
    }
    return render(request, 'core/review_user.html', context)

@login_required
def approve_club(request, club_id):
    """Aprova um clube pendente"""
    profile = ensure_profile_for_user(request.user)
    target_club = get_object_or_404(Club, id=club_id)

    if not profile.is_admin():
        messages.error(request, 'Você não tem permissão para aprovar este clube.')
        return redirect('dashboard')

    if target_club.is_approved():
        messages.warning(request, f'{target_club.name} já foi aprovado.')
        return redirect('pending_clubs')

    if request.method == 'POST':
        target_club.approve(request.user)
        messages.success(request, f'{target_club.name} foi aprovado com sucesso!')
        return redirect('pending_clubs')

    context = {
        'target_club': target_club,
        'action': 'approve'
    }
    return render(request, 'core/review_club.html', context)

@login_required
def reject_user(request, profile_id):
    """Rejeita uma conta de usuário"""
    profile = ensure_profile_for_user(request.user)
    target_profile = get_object_or_404(Profile, id=profile_id)
    
    # Verifica permissão
    if not profile.can_approve_user(target_profile):
        messages.error(request, 'Você não tem permissão para rejeitar este usuário.')
        return redirect('pending_approvals')
    
    # Se já foi rejeitado
    if target_profile.is_rejected():
        messages.warning(request, f'{target_profile.full_name} já foi rejeitado.')
        return redirect('pending_approvals')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Por favor, informe o motivo da rejeição.')
            return render(request, 'core/review_user.html', {
                'target_profile': target_profile,
                'action': 'reject'
            })
        
        try:
            target_profile.reject(request.user, reason)
            messages.info(request, f'{target_profile.full_name} foi rejeitado.')
        except PermissionError as e:
            messages.error(request, str(e))
        return redirect('pending_approvals')
    
    context = {
        'target_profile': target_profile,
        'action': 'reject'
    }
    return render(request, 'core/review_user.html', context)

@login_required
def reject_club(request, club_id):
    """Rejeita um clube pendente"""
    profile = ensure_profile_for_user(request.user)
    target_club = get_object_or_404(Club, id=club_id)

    if not profile.is_admin():
        messages.error(request, 'Você não tem permissão para rejeitar este clube.')
        return redirect('dashboard')

    if target_club.is_rejected():
        messages.warning(request, f'{target_club.name} já foi rejeitado.')
        return redirect('pending_clubs')

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Por favor, informe o motivo da rejeição.')
            return render(request, 'core/review_club.html', {
                'target_club': target_club,
                'action': 'reject'
            })

        target_club.reject(request.user, reason)
        messages.info(request, f'{target_club.name} foi rejeitado.')
        return redirect('pending_clubs')

    context = {
        'target_club': target_club,
        'action': 'reject'
    }
    return render(request, 'core/review_club.html', context)

@login_required
def my_approval_status(request):
    """Página para o usuário acompanhar o status do seu cadastro"""
    profile = ensure_profile_for_user(request.user)
    
    context = {
        'profile': profile,
        'status_display': profile.get_status_display_with_icon(),
        'review_info': profile.get_review_info(),
        'is_pending': profile.is_pending(),
        'is_approved': profile.is_approved(),
        'is_rejected': profile.is_rejected(),
    }
    return render(request, 'core/my_approval_status.html', context)

@login_required
def edit_profile(request):
    """Página para editar dados do usuário"""
    profile = ensure_profile_for_user(request.user)
    equipment_context = get_profile_equipment_context()
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        birth_date = request.POST.get('birth_date')
        phone = request.POST.get('phone')
        photo = request.FILES.get('photo')
        dominant_hand = parse_optional_fk(Handedness, request.POST.get('dominant_hand'))
        player_type = parse_optional_fk(PlayerType, request.POST.get('player_type'))
        blade = parse_optional_fk(Blade, request.POST.get('blade'))
        rubber_1 = parse_optional_fk(Rubber, request.POST.get('rubber_1'))
        rubber_2 = parse_optional_fk(Rubber, request.POST.get('rubber_2'))
        grip = parse_optional_fk(Grip, request.POST.get('grip'))
        
        # Validações
        if not full_name:
            messages.error(request, 'Nome completo é obrigatório.')
            context = {'profile': profile}
            context.update(equipment_context)
            return render(request, 'core/edit_profile.html', context)
        
        # Atualiza dados
        profile.full_name = full_name
        if birth_date:
            profile.birth_date = birth_date
        else:
            profile.birth_date = None
        if phone:
            profile.phone = phone
        else:
            profile.phone = ''
        if photo:
            profile.photo = photo
        profile.dominant_hand = dominant_hand
        profile.player_type = player_type
        profile.blade = blade
        profile.rubber_1 = rubber_1
        profile.rubber_2 = rubber_2
        profile.grip = grip
        
        profile.save()
        messages.success(request, 'Perfil atualizado com sucesso!')
        return redirect('dashboard')
    
    context = {'profile': profile}
    context.update(equipment_context)
    return render(request, 'core/edit_profile.html', context)