from django import forms
from .models import Tickets
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class TicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Tickets
        fields = ['status', 'technician']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Сохраняем оригинальные значения
        self.original_status = self.instance.status
        self.original_technician = self.instance.technician
        
        # По умолчанию ничего недоступно
        self.fields['status'].disabled = True
        self.fields['technician'].disabled = True
        
        if self.user is None:
            return
        
        # Суперпользователь игнорирует все ограничения
        if self.user.is_superuser:
            self.fields['status'].disabled = False
            self.fields['technician'].disabled = False
        else:
            # Проверяем группы для обычных пользователей
            is_dispatcher = self.user.groups.filter(name='dispatcher').exists()
            is_technician = self.user.groups.filter(name='technician').exists()
            
            # Диспетчер может менять и статус, и техника
            if is_dispatcher:
                self.fields['status'].disabled = False
                self.fields['technician'].disabled = False
            # Техник может менять только статус
            elif is_technician:
                self.fields['status'].disabled = False
            
        # Фильтр списка техников
        self.fields['technician'].queryset = User.objects.filter(
            groups__name='technician'
        )
    
    def clean(self):
        cleaned_data = super().clean()
        new_status = cleaned_data.get('status')
        
        # Если пользователь не суперпользователь, проверяем переход
        if self.user and not self.user.is_superuser:
            if new_status and new_status != self.original_status:
                allowed = self.instance.ALLOWED_TRANSITIONS.get(self.original_status, [])
                if new_status not in allowed:
                    raise ValidationError({
                        'status': f"Недопустимый переход из '{self.instance.get_status_display()}' в '{dict(self.instance.STATUS_CHOICES)[new_status]}'. Разрешенные переходы: {[dict(self.instance.STATUS_CHOICES)[s] for s in allowed]}"
                    })
        
        return cleaned_data
    
    def save(self, commit=True):
        new_status = self.cleaned_data.get('status')
        new_technician = self.cleaned_data.get('technician')
        
        # Для суперпользователя - прямое сохранение без валидации
        if self.user and self.user.is_superuser:
            self.instance.status = new_status
            self.instance.technician = new_technician
            
            # Обновляем closed_at если закрываем тикет
            if new_status == self.instance.STATUS_CLOSED and self.instance.closed_at is None:
                from django.utils import timezone
                self.instance.closed_at = timezone.now()
            
            if commit:
                # Используем update_fields чтобы избежать вызова change_status
                self.instance.save(update_fields=['status', 'technician', 'closed_at'])
            
            return self.instance
        
        # Для обычных пользователей
        status_changed = new_status != self.original_status
        technician_changed = new_technician != self.original_technician
        
        if not status_changed and not technician_changed:
            # Ничего не изменилось
            if commit:
                self.instance.save()
            return self.instance
        
        # Обновляем техника если изменился
        if technician_changed:
            self.instance.technician = new_technician
        
        # Если статус изменился, используем change_status для валидации
        if status_changed:
            if commit:
                try:
                    # Сначала сохраняем техника если он изменился
                    if technician_changed:
                        self.instance.save(update_fields=['technician'])
                    # Затем меняем статус через метод с валидацией
                    self.instance.change_status(new_status)
                except ValidationError as e:
                    # Если валидация не прошла, поднимаем ошибку
                    raise ValidationError({'status': str(e)})
        else:
            # Статус не изменился, только техник
            if commit:
                self.instance.save(update_fields=['technician'])
        
        return self.instance