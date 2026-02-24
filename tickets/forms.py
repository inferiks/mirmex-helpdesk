from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Tickets, Equipment, Comment

User = get_user_model()


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Tickets
        fields = ['equipment', 'title', 'description', 'priority', 'category', 'due_date']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['equipment'].queryset = Equipment.objects.all()
        self.fields['equipment'].empty_label = '--- Выберите оборудование (необязательно) ---'


class TicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Tickets
        fields = ['status', 'technician', 'priority', 'category', 'due_date']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.original_status = self.instance.status
        self.original_technician = self.instance.technician

        self.fields['due_date'].input_formats = ['%Y-%m-%dT%H:%M']

        self.fields['status'].disabled = True
        self.fields['technician'].disabled = True
        self.fields['priority'].disabled = True
        self.fields['category'].disabled = True
        self.fields['due_date'].disabled = True

        if self.user is None:
            return

        if self.user.is_superuser:
            for f in self.fields.values():
                f.disabled = False
        else:
            is_dispatcher = self.user.groups.filter(name='dispatcher').exists()
            is_technician = self.user.groups.filter(name='technician').exists()

            if is_dispatcher:
                for f in self.fields.values():
                    f.disabled = False
            elif is_technician:
                self.fields['status'].disabled = False

        self.fields['technician'].queryset = User.objects.filter(groups__name='technician')

    def clean(self):
        cleaned_data = super().clean()
        new_status = cleaned_data.get('status')

        if self.user and not self.user.is_superuser:
            if new_status and new_status != self.original_status:
                allowed = self.instance.ALLOWED_TRANSITIONS.get(self.original_status, [])
                if new_status not in allowed:
                    raise ValidationError({
                        'status': f"Недопустимый переход из «{self.instance.get_status_display()}» в «{dict(self.instance.STATUS_CHOICES)[new_status]}»."
                    })

        return cleaned_data

    def save(self, commit=True):
        new_status = self.cleaned_data.get('status')
        new_technician = self.cleaned_data.get('technician')

        if self.user and self.user.is_superuser:
            self.instance.status = new_status
            self.instance.technician = new_technician
            self.instance.priority = self.cleaned_data.get('priority', self.instance.priority)
            self.instance.category = self.cleaned_data.get('category', self.instance.category)
            self.instance.due_date = self.cleaned_data.get('due_date', self.instance.due_date)

            if new_status == self.instance.STATUS_CLOSED and self.instance.closed_at is None:
                from django.utils import timezone
                self.instance.closed_at = timezone.now()

            if commit:
                self.instance.save()
            return self.instance

        status_changed = new_status != self.original_status
        technician_changed = new_technician != self.original_technician

        if technician_changed:
            self.instance.technician = new_technician

        if status_changed:
            if commit:
                if technician_changed:
                    self.instance.save(update_fields=['technician'])
                try:
                    self.instance.change_status(new_status, changed_by=self.user)
                except ValidationError as e:
                    raise ValidationError({'status': str(e)})
        else:
            if commit:
                self.instance.save()

        return self.instance


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Добавьте комментарий к заявке...',
                'class': 'form-control',
            }),
        }
        labels = {
            'text': '',
        }


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['model', 'serial', 'location', 'status', 'purchased_at', 'notes']
        widgets = {
            'purchased_at': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class UserEditForm(forms.Form):
    ROLE_CHOICES = [
        ('reporter', 'Пользователь'),
        ('dispatcher', 'Диспетчер'),
        ('technician', 'Техник'),
        ('admin', 'Администратор'),
    ]

    first_name = forms.CharField(label='Имя', max_length=150, required=False)
    last_name = forms.CharField(label='Фамилия', max_length=150, required=False)
    email = forms.EmailField(label='Email', required=False)
    role = forms.ChoiceField(label='Роль', choices=ROLE_CHOICES)
    is_active = forms.BooleanField(label='Активен', required=False)


class ProfileForm(forms.Form):
    first_name = forms.CharField(label='Имя', max_length=150, required=False,
                                  widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label='Фамилия', max_length=150, required=False,
                                 widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label='Email', required=False,
                              widget=forms.EmailInput(attrs={'class': 'form-control'}))
