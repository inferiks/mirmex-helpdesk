from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.OutsourcingDashboardView.as_view(), name='outsourcing_dashboard'),

    # --- Справочники ---

    # Номенклатура
    path('nomenclature/', views.NomenclatureListView.as_view(), name='nomenclature_list'),
    path('nomenclature/create/', views.NomenclatureCreateView.as_view(), name='nomenclature_create'),
    path('nomenclature/<int:pk>/edit/', views.NomenclatureUpdateView.as_view(), name='nomenclature_edit'),
    path('nomenclature/<int:pk>/delete/', views.NomenclatureDeleteView.as_view(), name='nomenclature_delete'),

    # Клиенты
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    path('clients/create/', views.ClientCreateView.as_view(), name='client_create'),
    path('clients/<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('clients/<int:pk>/edit/', views.ClientUpdateView.as_view(), name='client_edit'),
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),

    # Конкуренты
    path('competitors/', views.CompetitorListView.as_view(), name='competitor_list'),
    path('competitors/create/', views.CompetitorCreateView.as_view(), name='competitor_create'),
    path('competitors/<int:pk>/edit/', views.CompetitorUpdateView.as_view(), name='competitor_edit'),
    path('competitors/<int:pk>/delete/', views.CompetitorDeleteView.as_view(), name='competitor_delete'),

    # Статьи затрат
    path('cost-items/', views.CostItemListView.as_view(), name='cost_item_list'),
    path('cost-items/create/', views.CostItemCreateView.as_view(), name='cost_item_create'),
    path('cost-items/<int:pk>/edit/', views.CostItemUpdateView.as_view(), name='cost_item_edit'),
    path('cost-items/<int:pk>/delete/', views.CostItemDeleteView.as_view(), name='cost_item_delete'),

    # Контрагенты
    path('counterparties/', views.CounterpartyListView.as_view(), name='counterparty_list'),
    path('counterparties/create/', views.CounterpartyCreateView.as_view(), name='counterparty_create'),
    path('counterparties/<int:pk>/edit/', views.CounterpartyUpdateView.as_view(), name='counterparty_edit'),
    path('counterparties/<int:pk>/delete/', views.CounterpartyDeleteView.as_view(), name='counterparty_delete'),

    # Ценностные предложения
    path('value-propositions/', views.ValuePropositionListView.as_view(), name='value_proposition_list'),
    path('value-propositions/create/', views.ValuePropositionCreateView.as_view(), name='value_proposition_create'),
    path('value-propositions/<int:pk>/edit/', views.ValuePropositionUpdateView.as_view(), name='value_proposition_edit'),
    path('value-propositions/<int:pk>/delete/', views.ValuePropositionDeleteView.as_view(), name='value_proposition_delete'),

    # --- Документы ---

    # Цены контрагентов
    path('counterparty-prices/', views.CounterpartyPricesDocumentListView.as_view(), name='cpd_list'),
    path('counterparty-prices/create/', views.CounterpartyPricesDocumentCreateView.as_view(), name='cpd_create'),
    path('counterparty-prices/<int:pk>/', views.CounterpartyPricesDocumentDetailView.as_view(), name='cpd_detail'),
    path('counterparty-prices/<int:pk>/edit/', views.CounterpartyPricesDocumentUpdateView.as_view(), name='cpd_edit'),
    path('counterparty-prices/<int:pk>/delete/', views.CounterpartyPricesDocumentDeleteView.as_view(), name='cpd_delete'),

    # Расчёт капитальных затрат
    path('capital-expenses/', views.CapitalExpensesDocumentListView.as_view(), name='ced_list'),
    path('capital-expenses/create/', views.CapitalExpensesDocumentCreateView.as_view(), name='ced_create'),
    path('capital-expenses/<int:pk>/', views.CapitalExpensesDocumentDetailView.as_view(), name='ced_detail'),
    path('capital-expenses/<int:pk>/edit/', views.CapitalExpensesDocumentUpdateView.as_view(), name='ced_edit'),
    path('capital-expenses/<int:pk>/delete/', views.CapitalExpensesDocumentDeleteView.as_view(), name='ced_delete'),

    # --- Регистры ---
    path('prices-register/', views.CounterpartyPricesRegisterView.as_view(), name='prices_register'),

    # --- Отчёты ---
    path('reports/capital-expenses/', views.CapitalExpensesReportView.as_view(), name='capital_expenses_report'),

    # --- AJAX ---
    path('api/counterparty-prices/', views.get_counterparty_prices, name='api_counterparty_prices'),
]
