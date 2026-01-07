from django.urls import path
from . import views

urlpatterns = [
    path('equipment/', views.EquipmentListView.as_view(), name='equipment_list'),
    path('equipment/<int:pk>/', views.EquipmentDetailView.as_view(), name="equipment_detail"),
    path('tickets/', views.TicketListView.as_view(), name="ticket_list"),
    path('tickets/create/', views.TicketCreateView.as_view(), name="ticket_create"),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name="ticket_detail"),
    path('tickets/<int:pk>/edit/', views.TicketUpdateView.as_view(), name='ticket_update'),
    path('tickets/<int:pk>/assign/', views.assign_ticket, name='ticket_assign'),
    path('tickets/<int:pk>/start/', views.start_ticket, name='ticket_start'),
    path('tickets/<int:pk>/close/', views.close_ticket, name='ticket_close'),

]
