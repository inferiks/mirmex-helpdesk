from django.urls import path
from . import views

urlpatterns = [
    # Equipment
    path('equipment/', views.EquipmentListView.as_view(), name='equipment_list'),
    path('equipment/create/', views.EquipmentCreateView.as_view(), name='equipment_create'),
    path('equipment/<int:pk>/', views.EquipmentDetailView.as_view(), name='equipment_detail'),
    path('equipment/<int:pk>/edit/', views.EquipmentUpdateView.as_view(), name='equipment_edit'),

    # Tickets
    path('tickets/', views.TicketListView.as_view(), name='ticket_list'),
    path('tickets/export/', views.TicketExportCSVView.as_view(), name='ticket_export'),
    path('tickets/create/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    path('tickets/<int:pk>/edit/', views.TicketUpdateView.as_view(), name='ticket_update'),
    path('tickets/<int:pk>/assign/', views.assign_ticket, name='ticket_assign'),
    path('tickets/<int:pk>/start/', views.start_ticket, name='ticket_start'),
    path('tickets/<int:pk>/close/', views.close_ticket, name='ticket_close'),
    path('tickets/<int:pk>/comment/', views.add_comment, name='ticket_comment'),

    # Kanban board
    path('kanban/', views.KanbanBoardView.as_view(), name='kanban'),

    # Search
    path('search/', views.SearchView.as_view(), name='search'),

    # Reports
    path('reports/', views.ReportsView.as_view(), name='reports'),

    # Profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),

    # User management
    path('users/', views.UserManagementView.as_view(), name='user_list'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
]
