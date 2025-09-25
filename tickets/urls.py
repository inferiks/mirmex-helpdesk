from django.urls import path
from . import views

urlpatterns = [
    path('equipment/', views.EquipmentListView.as_view(), name='equipment_list'),
    path('equipment/<int:pk>/', views.EquipmentDetailView.as_view(), name="equipment_detail"),
    path('tickets/', views.TicketListView.as_view(), name="ticket_list"),
    path('tickets/create/', views.TicketCreateView.as_view(), name="ticket_create"),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name="ticket_detail"),
]
