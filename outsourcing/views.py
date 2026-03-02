import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (CreateView, DeleteView, DetailView,
                                   ListView, UpdateView, View)

from .forms import (
    CapitalExpensesDocumentForm, CapitalExpensesItemFormSet,
    ClientForm, CompetitorForm, CostItemForm, CounterpartyForm,
    CounterpartyPricesDocumentForm, CounterpartyPricesItemFormSet,
    NomenclatureForm, ValuePropositionForm,
)
from .models import (
    CapitalExpensesDocument, CapitalExpensesRegister,
    Client, Competitor, CostItem, Counterparty,
    CounterpartyPricesDocument, CounterpartyPricesRegister,
    Nomenclature, ValueProposition, COST_TYPE_CHOICES,
)


# ---------------------------------------------------------------------------
# Dashboard / главная страница ИС
# ---------------------------------------------------------------------------

class OutsourcingDashboardView(LoginRequiredMixin, View):
    template_name = 'outsourcing/dashboard.html'

    def get(self, request):
        context = {
            'nomenclature_count': Nomenclature.objects.filter(is_group=False).count(),
            'clients_count': Client.objects.count(),
            'competitors_count': Competitor.objects.count(),
            'cost_items_count': CostItem.objects.filter(is_group=False).count(),
            'counterparties_count': Counterparty.objects.count(),
            'value_propositions_count': ValueProposition.objects.count(),
            'cpd_count': CounterpartyPricesDocument.objects.count(),
            'ced_count': CapitalExpensesDocument.objects.count(),
            'recent_cpd': CounterpartyPricesDocument.objects.select_related('counterparty').order_by('-date')[:5],
            'recent_ced': CapitalExpensesDocument.objects.select_related('value_proposition').order_by('-date')[:5],
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# Справочник: Номенклатура
# ---------------------------------------------------------------------------

class NomenclatureListView(LoginRequiredMixin, ListView):
    model = Nomenclature
    template_name = 'outsourcing/nomenclature_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        parent_id = self.request.GET.get('parent')
        if parent_id:
            return Nomenclature.objects.filter(parent_id=parent_id).order_by('-is_group', 'name')
        return Nomenclature.objects.filter(parent__isnull=True).order_by('-is_group', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parent_id = self.request.GET.get('parent')
        if parent_id:
            context['current_parent'] = get_object_or_404(Nomenclature, pk=parent_id)
        context['breadcrumbs'] = self._get_breadcrumbs(parent_id)
        return context

    def _get_breadcrumbs(self, parent_id):
        breadcrumbs = []
        if parent_id:
            obj = get_object_or_404(Nomenclature, pk=parent_id)
            while obj:
                breadcrumbs.insert(0, obj)
                obj = obj.parent
        return breadcrumbs


class NomenclatureCreateView(LoginRequiredMixin, CreateView):
    model = Nomenclature
    form_class = NomenclatureForm
    template_name = 'outsourcing/nomenclature_form.html'
    success_url = reverse_lazy('nomenclature_list')

    def get_initial(self):
        initial = super().get_initial()
        parent_id = self.request.GET.get('parent')
        if parent_id:
            initial['parent'] = parent_id
        is_group = self.request.GET.get('is_group', '0')
        initial['is_group'] = is_group == '1'
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Создать группу' if self.request.GET.get('is_group') == '1' else 'Добавить элемент'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Запись добавлена.')
        return super().form_valid(form)

    def get_success_url(self):
        parent = self.object.parent
        if parent:
            return reverse_lazy('nomenclature_list') + f'?parent={parent.pk}'
        return reverse_lazy('nomenclature_list')


class NomenclatureUpdateView(LoginRequiredMixin, UpdateView):
    model = Nomenclature
    form_class = NomenclatureForm
    template_name = 'outsourcing/nomenclature_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Редактировать: {self.object.name}'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Запись обновлена.')
        return super().form_valid(form)

    def get_success_url(self):
        parent = self.object.parent
        if parent:
            return reverse_lazy('nomenclature_list') + f'?parent={parent.pk}'
        return reverse_lazy('nomenclature_list')


class NomenclatureDeleteView(LoginRequiredMixin, DeleteView):
    model = Nomenclature
    template_name = 'outsourcing/confirm_delete.html'
    success_url = reverse_lazy('nomenclature_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'Номенклатура'
        return context


# ---------------------------------------------------------------------------
# Справочник: Клиенты
# ---------------------------------------------------------------------------

class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'outsourcing/client_list.html'
    context_object_name = 'clients'

    def get_queryset(self):
        qs = Client.objects.all()
        segment = self.request.GET.get('segment')
        if segment == 'b2b':
            qs = qs.filter(segment_b2b=True)
        elif segment == 'krasnodar':
            qs = qs.filter(segment_krasnodar=True)
        elif segment == 'rto':
            qs = qs.filter(segment_rto=True)
        elif segment == 'small_business':
            qs = qs.filter(segment_small_business=True)
        elif segment == 'medium_business':
            qs = qs.filter(segment_medium_business=True)
        elif segment == 'b2g':
            qs = qs.filter(segment_b2g=True)
        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_segment'] = self.request.GET.get('segment', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['total_count'] = Client.objects.count()
        return context


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'outsourcing/client_form.html'
    success_url = reverse_lazy('client_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Новый клиент'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Клиент добавлен.')
        return super().form_valid(form)


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'outsourcing/client_form.html'
    success_url = reverse_lazy('client_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Редактировать: {self.object.name}'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Клиент обновлён.')
        return super().form_valid(form)


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'outsourcing/client_detail.html'


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = 'outsourcing/confirm_delete.html'
    success_url = reverse_lazy('client_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'Клиент'
        return context


# ---------------------------------------------------------------------------
# Справочник: Конкуренты
# ---------------------------------------------------------------------------

class CompetitorListView(LoginRequiredMixin, ListView):
    model = Competitor
    template_name = 'outsourcing/competitor_list.html'
    context_object_name = 'competitors'

    def get_queryset(self):
        qs = Competitor.objects.all()
        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class CompetitorCreateView(LoginRequiredMixin, CreateView):
    model = Competitor
    form_class = CompetitorForm
    template_name = 'outsourcing/competitor_form.html'
    success_url = reverse_lazy('competitor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Новый конкурент'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Конкурент добавлен.')
        return super().form_valid(form)


class CompetitorUpdateView(LoginRequiredMixin, UpdateView):
    model = Competitor
    form_class = CompetitorForm
    template_name = 'outsourcing/competitor_form.html'
    success_url = reverse_lazy('competitor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Редактировать: {self.object.name}'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Конкурент обновлён.')
        return super().form_valid(form)


class CompetitorDeleteView(LoginRequiredMixin, DeleteView):
    model = Competitor
    template_name = 'outsourcing/confirm_delete.html'
    success_url = reverse_lazy('competitor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'Конкурент'
        return context


# ---------------------------------------------------------------------------
# Справочник: Статьи затрат
# ---------------------------------------------------------------------------

class CostItemListView(LoginRequiredMixin, ListView):
    model = CostItem
    template_name = 'outsourcing/cost_item_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        parent_id = self.request.GET.get('parent')
        if parent_id:
            return CostItem.objects.filter(parent_id=parent_id).order_by('-is_group', 'code', 'name')
        return CostItem.objects.filter(parent__isnull=True).order_by('-is_group', 'code', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parent_id = self.request.GET.get('parent')
        if parent_id:
            context['current_parent'] = get_object_or_404(CostItem, pk=parent_id)
        context['breadcrumbs'] = self._get_breadcrumbs(parent_id)
        return context

    def _get_breadcrumbs(self, parent_id):
        breadcrumbs = []
        if parent_id:
            obj = get_object_or_404(CostItem, pk=parent_id)
            while obj:
                breadcrumbs.insert(0, obj)
                obj = obj.parent
        return breadcrumbs


class CostItemCreateView(LoginRequiredMixin, CreateView):
    model = CostItem
    form_class = CostItemForm
    template_name = 'outsourcing/cost_item_form.html'
    success_url = reverse_lazy('cost_item_list')

    def get_initial(self):
        initial = super().get_initial()
        parent_id = self.request.GET.get('parent')
        if parent_id:
            initial['parent'] = parent_id
        is_group = self.request.GET.get('is_group', '0')
        initial['is_group'] = is_group == '1'
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Создать группу' if self.request.GET.get('is_group') == '1' else 'Добавить статью затрат'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Статья затрат добавлена.')
        return super().form_valid(form)

    def get_success_url(self):
        parent = self.object.parent
        if parent:
            return reverse_lazy('cost_item_list') + f'?parent={parent.pk}'
        return reverse_lazy('cost_item_list')


class CostItemUpdateView(LoginRequiredMixin, UpdateView):
    model = CostItem
    form_class = CostItemForm
    template_name = 'outsourcing/cost_item_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Редактировать: {self.object.name}'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Статья затрат обновлена.')
        return super().form_valid(form)

    def get_success_url(self):
        parent = self.object.parent
        if parent:
            return reverse_lazy('cost_item_list') + f'?parent={parent.pk}'
        return reverse_lazy('cost_item_list')


class CostItemDeleteView(LoginRequiredMixin, DeleteView):
    model = CostItem
    template_name = 'outsourcing/confirm_delete.html'
    success_url = reverse_lazy('cost_item_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'Статья затрат'
        return context


# ---------------------------------------------------------------------------
# Справочник: Контрагенты
# ---------------------------------------------------------------------------

class CounterpartyListView(LoginRequiredMixin, ListView):
    model = Counterparty
    template_name = 'outsourcing/counterparty_list.html'
    context_object_name = 'counterparties'

    def get_queryset(self):
        qs = Counterparty.objects.all()
        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class CounterpartyCreateView(LoginRequiredMixin, CreateView):
    model = Counterparty
    form_class = CounterpartyForm
    template_name = 'outsourcing/counterparty_form.html'
    success_url = reverse_lazy('counterparty_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Новый контрагент'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Контрагент добавлен.')
        return super().form_valid(form)


class CounterpartyUpdateView(LoginRequiredMixin, UpdateView):
    model = Counterparty
    form_class = CounterpartyForm
    template_name = 'outsourcing/counterparty_form.html'
    success_url = reverse_lazy('counterparty_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Редактировать: {self.object.name}'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Контрагент обновлён.')
        return super().form_valid(form)


class CounterpartyDeleteView(LoginRequiredMixin, DeleteView):
    model = Counterparty
    template_name = 'outsourcing/confirm_delete.html'
    success_url = reverse_lazy('counterparty_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'Контрагент'
        return context


# ---------------------------------------------------------------------------
# Справочник: Ценностные предложения
# ---------------------------------------------------------------------------

class ValuePropositionListView(LoginRequiredMixin, ListView):
    model = ValueProposition
    template_name = 'outsourcing/value_proposition_list.html'
    context_object_name = 'value_propositions'


class ValuePropositionCreateView(LoginRequiredMixin, CreateView):
    model = ValueProposition
    form_class = ValuePropositionForm
    template_name = 'outsourcing/value_proposition_form.html'
    success_url = reverse_lazy('value_proposition_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Новое ценностное предложение'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Ценностное предложение добавлено.')
        return super().form_valid(form)


class ValuePropositionUpdateView(LoginRequiredMixin, UpdateView):
    model = ValueProposition
    form_class = ValuePropositionForm
    template_name = 'outsourcing/value_proposition_form.html'
    success_url = reverse_lazy('value_proposition_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Редактировать: {self.object.name}'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Ценностное предложение обновлено.')
        return super().form_valid(form)


class ValuePropositionDeleteView(LoginRequiredMixin, DeleteView):
    model = ValueProposition
    template_name = 'outsourcing/confirm_delete.html'
    success_url = reverse_lazy('value_proposition_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'Ценностное предложение'
        return context


# ---------------------------------------------------------------------------
# AJAX: загрузка цен контрагента
# ---------------------------------------------------------------------------

@login_required
def get_counterparty_prices(request):
    """Возвращает JSON с ценами контрагента для подтягивания на форму документа."""
    counterparty_id = request.GET.get('counterparty_id')
    if not counterparty_id:
        return JsonResponse({'prices': []})

    prices = CounterpartyPricesRegister.objects.filter(
        counterparty_id=counterparty_id
    ).select_related('cost_item').values(
        'cost_item_id', 'cost_item__name', 'cost_type', 'price'
    )
    return JsonResponse({'prices': list(prices)})


# ---------------------------------------------------------------------------
# Документ: Цены контрагентов
# ---------------------------------------------------------------------------

class CounterpartyPricesDocumentListView(LoginRequiredMixin, ListView):
    model = CounterpartyPricesDocument
    template_name = 'outsourcing/cpd_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        return CounterpartyPricesDocument.objects.select_related('counterparty').order_by('-date')


class CounterpartyPricesDocumentDetailView(LoginRequiredMixin, DetailView):
    model = CounterpartyPricesDocument
    template_name = 'outsourcing/cpd_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related('cost_item').all()
        return context


class CounterpartyPricesDocumentCreateView(LoginRequiredMixin, View):
    template_name = 'outsourcing/cpd_form.html'

    def get(self, request):
        form = CounterpartyPricesDocumentForm()
        formset = CounterpartyPricesItemFormSet()
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'form_title': 'Новый документ: Цены контрагентов',
            'is_create': True,
        })

    def post(self, request):
        form = CounterpartyPricesDocumentForm(request.POST)
        formset = CounterpartyPricesItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            doc = form.save()
            formset.instance = doc
            formset.save()
            doc.post_document()
            messages.success(request, f'Документ №{doc.number} сохранён и проведён.')
            return redirect('cpd_detail', pk=doc.pk)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'form_title': 'Новый документ: Цены контрагентов',
            'is_create': True,
        })


class CounterpartyPricesDocumentUpdateView(LoginRequiredMixin, View):
    template_name = 'outsourcing/cpd_form.html'

    def get(self, request, pk):
        doc = get_object_or_404(CounterpartyPricesDocument, pk=pk)
        form = CounterpartyPricesDocumentForm(instance=doc)
        formset = CounterpartyPricesItemFormSet(instance=doc)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'document': doc,
            'form_title': f'Редактировать: {doc}',
            'is_create': False,
        })

    def post(self, request, pk):
        doc = get_object_or_404(CounterpartyPricesDocument, pk=pk)
        form = CounterpartyPricesDocumentForm(request.POST, instance=doc)
        formset = CounterpartyPricesItemFormSet(request.POST, instance=doc)
        if form.is_valid() and formset.is_valid():
            doc = form.save()
            formset.save()
            doc.post_document()
            messages.success(request, f'Документ №{doc.number} обновлён и перепроведён.')
            return redirect('cpd_detail', pk=doc.pk)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'document': doc,
            'form_title': f'Редактировать: {doc}',
            'is_create': False,
        })


class CounterpartyPricesDocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = CounterpartyPricesDocument
    template_name = 'outsourcing/confirm_delete.html'
    success_url = reverse_lazy('cpd_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'Документ цен контрагентов'
        return context


# ---------------------------------------------------------------------------
# Документ: Расчёт капитальных затрат
# ---------------------------------------------------------------------------

class CapitalExpensesDocumentListView(LoginRequiredMixin, ListView):
    model = CapitalExpensesDocument
    template_name = 'outsourcing/ced_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        return CapitalExpensesDocument.objects.select_related('value_proposition').order_by('-date')


class CapitalExpensesDocumentDetailView(LoginRequiredMixin, DetailView):
    model = CapitalExpensesDocument
    template_name = 'outsourcing/ced_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items = self.object.items.select_related('cost_item', 'counterparty').all()
        context['items'] = items
        context['total'] = self.object.get_total()
        return context


class CapitalExpensesDocumentCreateView(LoginRequiredMixin, View):
    template_name = 'outsourcing/ced_form.html'

    def get(self, request):
        form = CapitalExpensesDocumentForm()
        formset = CapitalExpensesItemFormSet()
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'form_title': 'Новый документ: Расчёт капитальных затрат',
            'is_create': True,
            'counterparties_json': self._counterparties_json(),
        })

    def post(self, request):
        form = CapitalExpensesDocumentForm(request.POST)
        formset = CapitalExpensesItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            doc = form.save()
            formset.instance = doc
            formset.save()
            doc.post_document()
            messages.success(request, f'Документ №{doc.number} сохранён и проведён.')
            return redirect('ced_detail', pk=doc.pk)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'form_title': 'Новый документ: Расчёт капитальных затрат',
            'is_create': True,
            'counterparties_json': self._counterparties_json(),
        })

    def _counterparties_json(self):
        data = {}
        for reg in CounterpartyPricesRegister.objects.select_related('cost_item', 'counterparty'):
            key = f"{reg.cost_item_id}_{reg.cost_type}"
            data[key] = {
                'counterparty_id': reg.counterparty_id,
                'counterparty_name': str(reg.counterparty),
                'price': str(reg.price),
            }
        return json.dumps(data)


class CapitalExpensesDocumentUpdateView(LoginRequiredMixin, View):
    template_name = 'outsourcing/ced_form.html'

    def get(self, request, pk):
        doc = get_object_or_404(CapitalExpensesDocument, pk=pk)
        form = CapitalExpensesDocumentForm(instance=doc)
        formset = CapitalExpensesItemFormSet(instance=doc)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'document': doc,
            'form_title': f'Редактировать: {doc}',
            'is_create': False,
            'counterparties_json': self._counterparties_json(),
        })

    def post(self, request, pk):
        doc = get_object_or_404(CapitalExpensesDocument, pk=pk)
        form = CapitalExpensesDocumentForm(request.POST, instance=doc)
        formset = CapitalExpensesItemFormSet(request.POST, instance=doc)
        if form.is_valid() and formset.is_valid():
            doc = form.save()
            formset.save()
            doc.post_document()
            messages.success(request, f'Документ №{doc.number} обновлён и перепроведён.')
            return redirect('ced_detail', pk=doc.pk)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'document': doc,
            'form_title': f'Редактировать: {doc}',
            'is_create': False,
            'counterparties_json': self._counterparties_json(),
        })

    def _counterparties_json(self):
        data = {}
        for reg in CounterpartyPricesRegister.objects.select_related('cost_item', 'counterparty'):
            key = f"{reg.cost_item_id}_{reg.cost_type}"
            data[key] = {
                'counterparty_id': reg.counterparty_id,
                'counterparty_name': str(reg.counterparty),
                'price': str(reg.price),
            }
        return json.dumps(data)


class CapitalExpensesDocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = CapitalExpensesDocument
    template_name = 'outsourcing/confirm_delete.html'
    success_url = reverse_lazy('ced_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'Документ расчёта капитальных затрат'
        return context


# ---------------------------------------------------------------------------
# Отчёт: Структура капитальных затрат
# ---------------------------------------------------------------------------

class CapitalExpensesReportView(LoginRequiredMixin, View):
    template_name = 'outsourcing/capital_expenses_report.html'

    def get(self, request):
        value_propositions = ValueProposition.objects.all()
        vp_filter = request.GET.getlist('vp')
        if vp_filter:
            value_propositions = value_propositions.filter(pk__in=vp_filter)

        # Все уникальные статьи затрат в регистре
        register_qs = CapitalExpensesRegister.objects.select_related(
            'cost_item', 'value_proposition', 'cost_item__parent'
        )
        if vp_filter:
            register_qs = register_qs.filter(value_proposition_id__in=vp_filter)

        # Строим структуру отчёта
        # { (cost_item_id, cost_type): { vp_id: total } }
        report_data = {}
        for entry in register_qs:
            key = (entry.cost_item_id, entry.cost_type)
            if key not in report_data:
                report_data[key] = {
                    'cost_item': entry.cost_item,
                    'cost_type': entry.cost_type,
                    'cost_type_display': entry.get_cost_type_display(),
                    'vp_totals': {},
                    'row_total': Decimal('0'),
                }
            report_data[key]['vp_totals'][entry.value_proposition_id] = \
                report_data[key]['vp_totals'].get(entry.value_proposition_id, Decimal('0')) + entry.total
            report_data[key]['row_total'] += entry.total

        # Итоги по столбцам (по ценностным предложениям)
        vp_totals = {}
        grand_total = Decimal('0')
        for row in report_data.values():
            for vp_id, total in row['vp_totals'].items():
                vp_totals[vp_id] = vp_totals.get(vp_id, Decimal('0')) + total
            grand_total += row['row_total']

        # Сортировка строк
        sorted_rows = sorted(report_data.values(), key=lambda r: (r['cost_item'].get_full_path(), r['cost_type']))

        # Строим список vp_values для каждой строки (выровнен по value_propositions)
        vp_list = list(value_propositions)
        rows = []
        for row in sorted_rows:
            vp_values = [row['vp_totals'].get(vp.pk) for vp in vp_list]
            rows.append({
                'cost_item': row['cost_item'],
                'cost_type': row['cost_type'],
                'cost_type_display': row['cost_type_display'],
                'vp_values': vp_values,
                'row_total': row['row_total'],
            })

        # Итоги по столбцам (выровнены по vp_list)
        col_totals = [vp_totals.get(vp.pk, Decimal('0')) for vp in vp_list]

        all_vps = ValueProposition.objects.all()

        context = {
            'rows': rows,
            'value_propositions': vp_list,
            'all_vps': all_vps,
            'selected_vps': [int(v) for v in vp_filter] if vp_filter else [],
            'col_totals': col_totals,
            'grand_total': grand_total,
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# Регистр цен контрагентов (просмотр)
# ---------------------------------------------------------------------------

class CounterpartyPricesRegisterView(LoginRequiredMixin, ListView):
    model = CounterpartyPricesRegister
    template_name = 'outsourcing/prices_register.html'
    context_object_name = 'entries'

    def get_queryset(self):
        qs = CounterpartyPricesRegister.objects.select_related(
            'counterparty', 'cost_item', 'document'
        )
        counterparty_filter = self.request.GET.get('counterparty')
        if counterparty_filter:
            qs = qs.filter(counterparty_id=counterparty_filter)
        return qs.order_by('counterparty', 'cost_item')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['counterparties'] = Counterparty.objects.all()
        context['selected_counterparty'] = self.request.GET.get('counterparty', '')
        return context
