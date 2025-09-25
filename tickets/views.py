from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from .models import Equipment, Tickets
from django.contrib.auth.mixins import LoginRequiredMixin

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
    
class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Tickets
    template_name = 'tickets/ticket_detail.html'
    
class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Tickets
    template_name = 'tickets/ticket_form.html'
    fields = ['equipment', 'title', 'description']
    success_url = reverse_lazy('ticket_list')
    
    def form_valid(self, form):
        form.instance.reporter = self.request.user
        return super().form_valid(form)
    