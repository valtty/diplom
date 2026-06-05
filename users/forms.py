from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    """Форма регистрации (только клиенты)"""

    phone = forms.CharField(
        label='Телефон',
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'})
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'CLIENT'  # Всегда регистрируем как клиента
        user.phone = self.cleaned_data['phone']

        if commit:
            user.save()

        return user


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'avatar', 'role')

