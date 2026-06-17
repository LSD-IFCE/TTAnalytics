from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """
    Formulário de criação de usuário personalizado
    """
    
    full_name = forms.CharField(
        max_length=255,
        required=True,
        label='Nome Completo'
    )
    
    email = forms.EmailField(
        required=True,
        label='E-mail'
    )
    
    birth_date = forms.DateField(
        required=True,
        label='Data de Nascimento',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'full_name',
            'birth_date',
            'password1',
            'password2',
        )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        return email

class CustomUserChangeForm(UserChangeForm):
    """
    Formulário de edição de usuário personalizado
    """
    
    full_name = forms.CharField(
        max_length=255,
        required=True,
        label='Nome Completo'
    )
    
    birth_date = forms.DateField(
        required=True,
        label='Data de Nascimento',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'full_name',
            'birth_date',
            'is_active',
            'is_staff',
            'is_superuser',
        )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        return email