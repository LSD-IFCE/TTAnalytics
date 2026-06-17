from django import forms

from clubs.models import Club
from equipment.models import Blade, Grip, Handedness, PlayerType, Rubber


class ManagedUserCreateForm(forms.Form):
    username = forms.CharField(max_length=150, label='Usuário')
    full_name = forms.CharField(max_length=255, label='Nome Completo')
    email = forms.EmailField(label='E-mail')
    birth_date = forms.DateField(
        required=False,
        label='Data de Nascimento',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    photo = forms.ImageField(required=False, label='Foto')
    club = forms.ModelChoiceField(
        queryset=Club.objects.filter(is_active=True).order_by('name'),
        required=False,
        label='Clube'
    )
    dominant_hand = forms.ModelChoiceField(
        queryset=Handedness.objects.filter(is_active=True).order_by('name'),
        required=False,
        label='Mão Dominante'
    )
    player_type = forms.ModelChoiceField(
        queryset=PlayerType.objects.filter(is_active=True).order_by('name'),
        required=False,
        label='Tipo'
    )
    blade = forms.ModelChoiceField(
        queryset=Blade.objects.filter(is_active=True).select_related('brand').order_by('brand__name', 'name'),
        required=False,
        label='Madeira'
    )
    rubber_1 = forms.ModelChoiceField(
        queryset=Rubber.objects.filter(is_active=True).select_related('brand').order_by('brand__name', 'name'),
        required=False,
        label='Borracha 1'
    )
    rubber_2 = forms.ModelChoiceField(
        queryset=Rubber.objects.filter(is_active=True).select_related('brand').order_by('brand__name', 'name'),
        required=False,
        label='Borracha 2'
    )
    grip = forms.ModelChoiceField(
        queryset=Grip.objects.filter(is_active=True).order_by('name'),
        required=False,
        label='Empunhadura'
    )
    password1 = forms.CharField(widget=forms.PasswordInput(), label='Senha')
    password2 = forms.CharField(widget=forms.PasswordInput(), label='Confirmar Senha')

    def __init__(self, *args, lock_club=False, fixed_club=None, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

        if fixed_club is not None:
            self.fields['club'].initial = fixed_club

        if lock_club:
            self.fields['club'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            self.add_error('password2', 'As senhas não coincidem.')
        return cleaned_data


class ManagedClubCreateForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ['name', 'acronym', 'address', 'city', 'state', 'phone', 'email', 'website', 'logo']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css_class = 'form-control'
            if isinstance(field.widget, forms.ClearableFileInput):
                css_class = 'form-control'
            field.widget.attrs['class'] = css_class

        self.fields['state'].widget.attrs['maxlength'] = 2