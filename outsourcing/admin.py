from django.contrib import admin

from .models import (
    Nomenclature, Client, Competitor, CostItem, Counterparty, ValueProposition,
    CounterpartyPricesDocument, CounterpartyPricesItem, CounterpartyPricesRegister,
    CapitalExpensesDocument, CapitalExpensesItem, CapitalExpensesRegister,
)


@admin.register(Nomenclature)
class NomenclatureAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_group', 'code']
    list_filter = ['is_group']
    search_fields = ['name', 'code']


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'segment_b2b', 'segment_krasnodar', 'segment_rto']
    list_filter = ['segment_b2b', 'segment_krasnodar', 'segment_rto', 'segment_small_business']
    search_fields = ['name', 'email']


@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'website']
    search_fields = ['name']


@admin.register(CostItem)
class CostItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_group', 'code']
    list_filter = ['is_group']
    search_fields = ['name', 'code']


@admin.register(Counterparty)
class CounterpartyAdmin(admin.ModelAdmin):
    list_display = ['name', 'inn', 'phone', 'email']
    search_fields = ['name', 'inn']


@admin.register(ValueProposition)
class ValuePropositionAdmin(admin.ModelAdmin):
    list_display = ['name', 'target_segment']
    search_fields = ['name']


class CounterpartyPricesItemInline(admin.TabularInline):
    model = CounterpartyPricesItem
    extra = 1


@admin.register(CounterpartyPricesDocument)
class CounterpartyPricesDocumentAdmin(admin.ModelAdmin):
    list_display = ['number', 'date', 'counterparty']
    inlines = [CounterpartyPricesItemInline]


@admin.register(CounterpartyPricesRegister)
class CounterpartyPricesRegisterAdmin(admin.ModelAdmin):
    list_display = ['counterparty', 'cost_item', 'cost_type', 'price', 'date']
    list_filter = ['cost_type', 'counterparty']


class CapitalExpensesItemInline(admin.TabularInline):
    model = CapitalExpensesItem
    extra = 1


@admin.register(CapitalExpensesDocument)
class CapitalExpensesDocumentAdmin(admin.ModelAdmin):
    list_display = ['number', 'date', 'value_proposition']
    inlines = [CapitalExpensesItemInline]


@admin.register(CapitalExpensesRegister)
class CapitalExpensesRegisterAdmin(admin.ModelAdmin):
    list_display = ['value_proposition', 'cost_item', 'cost_type', 'total', 'document']
    list_filter = ['cost_type', 'value_proposition']
