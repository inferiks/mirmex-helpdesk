from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from .models import Equipment, Tickets
from .forms import TicketUpdateForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError

User = get_user_model()

def is_admin_or_dispatcher(user):
    return (
            user.is_superuser or
            user.groups.filter(name__in=['admin', 'dispatcher']).exists()
        )
    
def is_technician(user):
    return user.groups.filter(name='technician').exists()

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
        
        if is_admin_or_dispatcher(user):
            return Tickets.objects.all()

        if is_technician(user):
            return Tickets.objects.filter(technician=user)

        return Tickets.objects.filter(reporter=user)

    
class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Tickets
    template_name = 'tickets/ticket_detail.html'
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if is_admin_or_dispatcher(user):
            return qs

        if is_technician(user):
            return qs.filter(technician=user)

        return qs.filter(reporter=user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_assign'] = is_admin_or_dispatcher(self.request.user)
        context['can_change_status'] = (
            is_admin_or_dispatcher(self.request.user) or
            is_technician(self.request.user)
        )
        # Добавляем флаг для показа кнопки редактирования
        context['can_edit_directly'] = self.request.user.is_superuser
        return context

        
class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Tickets
    template_name = 'tickets/ticket_form.html'
    fields = ['equipment', 'title', 'description']
    success_url = reverse_lazy('ticket_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(
            name__in=["admin", "dispatcher", "reporter"]
        ).exists()):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.reporter = self.request.user
        return super().form_valid(form)

class TicketUpdateView(LoginRequiredMixin, UpdateView):
    model = Tickets
    form_class = TicketUpdateForm
    template_name = 'tickets/ticket_update.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Только суперпользователь может использовать форму прямого редактирования
        if not request.user.is_superuser:
            raise PermissionDenied("Только администратор может напрямую редактировать тикеты. Используйте специальные кнопки для изменения статуса.")
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        # Суперпользователь видит все тикеты
        return Tickets.objects.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('ticket_detail', kwargs={'pk': self.object.pk})
    
# Action views
@login_required
def assign_ticket(request, pk):
    ticket = get_object_or_404(Tickets, pk=pk)
    
    if not is_admin_or_dispatcher(request.user):
        raise PermissionDenied
    
    if request.method == 'POST':
        technician_id = request.POST.get('technician')
        technician = get_object_or_404(User, pk=technician_id)
        try:
            ticket.assign(technician)
        except ValidationError as e:
            messages.error(request, e)
        else:
            messages.success(request, f"Техник {technician.username} назначен.")
        return redirect('ticket_detail', pk=pk)
    
    technicians = User.objects.filter(groups__name='technician')
    return render(request, 'tickets/ticket_assign.html', {
        'ticket': ticket,
        'technicians': technicians,
    })
    
    
@login_required
def start_ticket(request, pk):
    ticket = get_object_or_404(Tickets, pk=pk)
    
    if not (is_admin_or_dispatcher(request.user) or request.user == ticket.technician):
        raise PermissionDenied

    try:
        ticket.start_work()
    except ValidationError as e:
        messages.error(request, e)
    else:
        messages.success(request, "Статус изменен на 'В работе'.")
    
    return redirect('ticket_detail', pk=pk)


@login_required
def close_ticket(request, pk):
    ticket = get_object_or_404(Tickets, pk=pk)
    
    if not (is_admin_or_dispatcher(request.user) or request.user == ticket.technician):
        raise PermissionDenied
    
    try:
        ticket.close()
    except ValidationError as e:
        messages.error(request, e)
    else:
        messages.success(request, "Тикет закрыт.")
    
    return redirect('ticket_detail', pk=pk)