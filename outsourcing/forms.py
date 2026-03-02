from django import forms
from django.forms import inlineformset_factory

from .models import (
    Nomenclature, Client, Competitor, CostItem, Counterparty, ValueProposition,
    CounterpartyPricesDocument, CounterpartyPricesItem,
    CapitalExpensesDocument, CapitalExpensesItem,
    COST_TYPE_CHOICES,
)


class NomenclatureForm(forms.ModelForm):
    class Meta:
        model = Nomenclature
        fields = ['parent', 'name', 'is_group', 'code', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = Nomenclature.objects.filter(is_group=True)
        self.fields['parent'].empty_label = '--- Корневой уровень ---'


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'name', 'contact_person', 'phone', 'email', 'address',
            'segment_b2b', 'segment_krasnodar', 'segment_rto',
            'segment_small_business', 'segment_medium_business', 'segment_b2g',
            'note',
        ]
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ссылка на web-ресурс...'}),
        }


class CompetitorForm(forms.ModelForm):
    class Meta:
        model = Competitor
        fields = ['name', 'address', 'phone', 'website', 'note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ссылка на web-ресурс...'}),
        }


class CostItemForm(forms.ModelForm):
    class Meta:
        model = CostItem
        fields = ['parent', 'name', 'is_group', 'code']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = CostItem.objects.filter(is_group=True)
        self.fields['parent'].empty_label = '--- Корневой уровень ---'


class CounterpartyForm(forms.ModelForm):
    class Meta:
        model = Counterparty
        fields = ['name', 'address', 'phone', 'email', 'inn', 'website']


class ValuePropositionForm(forms.ModelForm):
    class Meta:
        model = ValueProposition
        fields = ['name', 'description', 'target_segment']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


# ---------------------------------------------------------------------------
# Документ «Цены контрагентов»
# ---------------------------------------------------------------------------

class CounterpartyPricesDocumentForm(forms.ModelForm):
    class Meta:
        model = CounterpartyPricesDocument
        fields = ['date', 'counterparty', 'comment']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'comment': forms.Textarea(attrs={'rows': 2}),
        }


class CounterpartyPricesItemForm(forms.ModelForm):
    class Meta:
        model = CounterpartyPricesItem
        fields = ['cost_item', 'cost_type', 'price']
        widgets = {
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cost_item'].queryset = CostItem.objects.filter(is_group=False)


CounterpartyPricesItemFormSet = inlineformset_factory(
    CounterpartyPricesDocument,
    CounterpartyPricesItem,
    form=CounterpartyPricesItemForm,
    extra=3,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# Документ «Расчёт капитальных затрат»
# ---------------------------------------------------------------------------

class CapitalExpensesDocumentForm(forms.ModelForm):
    class Meta:
        model = CapitalExpensesDocument
        fields = ['date', 'value_proposition', 'comment']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'comment': forms.Textarea(attrs={'rows': 2}),
        }


class CapitalExpensesItemForm(forms.ModelForm):
    class Meta:
        model = CapitalExpensesItem
        fields = ['cost_item', 'cost_type', 'counterparty', 'price', 'quantity']
        widgets = {
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'price-field'}),
            'quantity': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'value': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cost_item'].queryset = CostItem.objects.filter(is_group=False)
        self.fields['counterparty'].required = False
        self.fields['counterparty'].empty_label = '--- Выберите контрагента ---'


CapitalExpensesItemFormSet = inlineformset_factory(
    CapitalExpensesDocument,
    CapitalExpensesItem,
    form=CapitalExpensesItemForm,
    extra=3,
    can_delete=True,
)
