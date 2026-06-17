from django import forms

from .models import Brand, Blade, Rubber


class BaseEquipmentForm(forms.ModelForm):
    """Configuração visual comum para formulários de equipamento."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            css_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{css_class} form-control'.strip()

        if 'description' in self.fields:
            self.fields['description'].widget = forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Adicione detalhes que ajudem a identificar o equipamento.'
            })

        if 'brand' in self.fields:
            self.fields['brand'].queryset = Brand.objects.filter(is_active=True).order_by('name')
            self.fields['brand'].empty_label = 'Selecione uma marca'
            self.fields['brand'].widget.attrs['class'] = 'form-select'


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ex.: Butterfly, DHS, Tibhar'
        })


class RubberForm(BaseEquipmentForm):
    class Meta:
        model = Rubber
        fields = [
            'name', 'brand', 'category', 'rubber_type',
            'thickness', 'color', 'description'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'rubber_type': forms.Select(attrs={'class': 'form-select'}),
        }


class BladeForm(BaseEquipmentForm):
    class Meta:
        model = Blade
        fields = [
            'name', 'brand', 'blade_type', 'speed_class',
            'weight', 'layers', 'handle', 'description'
        ]
        widgets = {
            'blade_type': forms.Select(attrs={'class': 'form-select'}),
            'speed_class': forms.Select(attrs={'class': 'form-select'}),
        }