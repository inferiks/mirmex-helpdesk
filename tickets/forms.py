from django import forms
from .models import Tickets
from django.contrib.auth import get_user_model

User = get_user_model()

class TicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Tickets
        fields = ['status', 'technician']
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # По умолчание ничего недоступно
        self.fields['status'].disabled = True
        self.fields['technician'].disabled = True
        
        if user is None:
            return
        
        # может менять статус
        if user.has_perm('tickets.can_change_status'):
            self.fields['status'].disabled = False
        
        # может назначить техника
        if user.has_perm('tickets.can_assign_ticket'):
            self.fields['technician'].disabled = False
            
        # Фильтр списка техников
        self.fields['technician'].queryset = User.objects.filter(
            groups__name='technician'
        ) 