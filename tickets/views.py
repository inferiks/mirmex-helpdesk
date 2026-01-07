from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from .models import Equipment, Tickets
from .forms import TicketUpdateForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
User = get_user_model()

# Equipment
class EquipmentListView(LoginRequiredMixin, ListView):
    model = Equipment
    template_name = 'tickets/equipments_list.html'
    
class EquipmentDetailView(LoginRequiredMixin, DetailView):
    model = Equipment
    template_name = 'tickets/equipment_detail.html'
   
# Tickets 
class TicketListView(LoginRequiredMixin, ListView):
    model = Tickets
    template_name = 'tickets/ticket_list.html'
    
    def get_queryset(self):
        user = self.request.user
        
        # admin и dispatcher видят все заявки
        if user.is_superuser or user.groups.filter(name__in=["admin", "dispatcher"]).exists():
            return Tickets.objects.all()
        
        # technician видит только назначенные ему
        if user.groups.filter(name__in=["technician"]).exists():
            return Tickets.objects.filter(technician=user)
        
        # reporter видит только свои репорты
        return Tickets.objects.filter(reporter=user)
    
class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Tickets
    template_name = 'tickets/ticket_detail.html'
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser or user.groups.filter(name__in=["admin", "dispatcher"]).exists():
            return qs
        
        if user.is_superuser or user.groups.filter(name__in=["technician"]).exists():
            return qs.filter(technician=user)
        
        return qs.filter(reporter=user)
        
class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Tickets
    template_name = 'tickets/ticket_form.html'
    fields = ['equipment', 'title', 'description', 'technician']
    success_url = reverse_lazy('ticket_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        
        if user.is_superuser or user.groups.filter(name__in=['admin', 'dispatcher']).exists():
            # admin/dispatcher видят поле technician
            form.fields['technician'].queryset = User.objects.filter(groups__name='technician')
        else:
            # обычный репортер не видит это поле
            form.fields.pop('technician', None)
            
        return form
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        
        if not (user.is_superuser or user.groups.filter(name__in=["admin", "dispatcher", "reporter"]).exists()):
            raise PermissionDenied
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        if not self.request.user.groups.filter(name__in=['admin', 'dispatcher']).exists():
            form.instance.technician = None
        form.instance.reporter = self.request.user
        return super().form_valid(form)

class TicketUpdateView(LoginRequiredMixin, UpdateView):
    model = Tickets
    form_class = TicketUpdateForm
    template_name = 'tickets/ticket_update.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user        
        return kwargs
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        # админ и диспетчер видят всё
        if user.groups.filter(name__in=['admin', 'dispatcher']).exists():
            return qs
        
        # техник видит только свои тикеты
        if user.groups.filter(name='technician').exists():
            return qs.filter(technician=user)
        
        return qs.none()
    
    def get_success_url(self):
        return reverse_lazy('ticket_detail', kwargs={'pk': self.object.pk})