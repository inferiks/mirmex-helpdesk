import csv
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import (Avg, Count, DurationField, ExpressionWrapper,
                               F, Q)
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (CreateView, DetailView, ListView,
                                   UpdateView, View)

from .forms import (CommentForm, EquipmentForm, ProfileForm, TicketCreateForm,
                    TicketUpdateForm, UserEditForm, UserRegistrationForm)
from .models import Comment, Equipment, TicketHistory, Tickets

User = get_user_model()


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def is_admin_or_dispatcher(user):
    return (
        user.is_superuser or
        user.groups.filter(name__in=['admin', 'dispatcher']).exists()
    )


def is_technician(user):
    return user.groups.filter(name='technician').exists()


def get_user_role(user):
    if user.is_superuser or user.groups.filter(name='admin').exists():
        return 'admin'
    if user.groups.filter(name='dispatcher').exists():
        return 'dispatcher'
    if user.groups.filter(name='technician').exists():
        return 'technician'
    return 'reporter'


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

class EquipmentListView(LoginRequiredMixin, ListView):
    model = Equipment
    template_name = 'tickets/equipments_list.html'


class EquipmentDetailView(LoginRequiredMixin, DetailView):
    model = Equipment
    template_name = 'tickets/equipment_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_ticket_count'] = self.object.tickets.exclude(status='closed').count()
        context['can_edit'] = is_admin_or_dispatcher(self.request.user)
        return context


class EquipmentCreateView(LoginRequiredMixin, CreateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'tickets/equipment_form.html'
    success_url = reverse_lazy('equipment_list')

    def dispatch(self, request, *args, **kwargs):
        if not is_admin_or_dispatcher(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Добавить оборудование'
        context['is_create'] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Оборудование успешно добавлено.')
        return super().form_valid(form)


class EquipmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'tickets/equipment_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not is_admin_or_dispatcher(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Редактировать: {self.object.model}'
        context['is_create'] = False
        return context

    def get_success_url(self):
        return reverse_lazy('equipment_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Оборудование обновлено.')
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------

class TicketListView(LoginRequiredMixin, ListView):
    model = Tickets
    template_name = 'tickets/ticket_list.html'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user

        if is_admin_or_dispatcher(user):
            queryset = Tickets.objects.select_related('reporter', 'technician', 'equipment')
        elif is_technician(user):
            queryset = Tickets.objects.filter(technician=user).select_related('reporter', 'technician', 'equipment')
        else:
            queryset = Tickets.objects.filter(reporter=user).select_related('reporter', 'technician', 'equipment')

        # Filters
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        priority_filter = self.request.GET.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)

        category_filter = self.request.GET.get('category')
        if category_filter:
            queryset = queryset.filter(category=category_filter)

        technician_filter = self.request.GET.get('technician')
        if technician_filter and is_admin_or_dispatcher(user):
            if technician_filter == 'none':
                queryset = queryset.filter(technician__isnull=True)
            else:
                queryset = queryset.filter(technician_id=technician_filter)

        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(id__icontains=search_query)
            )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if is_admin_or_dispatcher(user):
            base_qs = Tickets.objects.all()
        elif is_technician(user):
            base_qs = Tickets.objects.filter(technician=user)
        else:
            base_qs = Tickets.objects.filter(reporter=user)

        context['is_admin_or_dispatcher'] = is_admin_or_dispatcher(user)
        context['count_new'] = base_qs.filter(status='new').count()
        context['count_assigned'] = base_qs.filter(status='assigned').count()
        context['count_in_progress'] = base_qs.filter(status='in_progress').count()
        context['count_closed'] = base_qs.filter(status='closed').count()

        context['current_status'] = self.request.GET.get('status', '')
        context['current_priority'] = self.request.GET.get('priority', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_technician'] = self.request.GET.get('technician', '')
        context['search_query'] = self.request.GET.get('q', '')

        context['priority_choices'] = Tickets.PRIORITY_CHOICES
        context['category_choices'] = Tickets.CATEGORY_CHOICES
        context['status_choices'] = Tickets.STATUS_CHOICES

        if is_admin_or_dispatcher(user):
            context['technicians'] = User.objects.filter(groups__name='technician')

        has_filter = any([
            context['current_status'], context['current_priority'],
            context['current_category'], context['current_technician'],
            context['search_query'],
        ])
        context['has_filter'] = has_filter

        # Overdue count
        now = timezone.now()
        context['count_overdue'] = base_qs.filter(
            due_date__lt=now,
            status__in=['new', 'assigned', 'in_progress']
        ).count()

        # Query params without 'page' for pagination links
        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_params'] = params.urlencode()

        # Limited page range for pagination widget
        if context.get('is_paginated'):
            page_obj = context['page_obj']
            paginator = context['paginator']
            current = page_obj.number
            total = paginator.num_pages
            start = max(1, current - 3)
            end = min(total, current + 3)
            context['page_range'] = range(start, end + 1)
            context['show_first'] = start > 1
            context['show_last'] = end < total

        return context


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
        user = self.request.user
        ticket = self.object

        context['can_assign'] = is_admin_or_dispatcher(user)
        context['can_change_status'] = is_admin_or_dispatcher(user) or is_technician(user)
        context['can_edit_directly'] = user.is_superuser
        context['is_overdue'] = ticket.is_overdue()
        context['comments'] = ticket.comments.select_related('author').all()
        context['history'] = ticket.history.select_related('changed_by').order_by('timestamp')
        context['comment_form'] = CommentForm()

        # SLA progress bar
        sla_percent = None
        sla_color = 'success'
        if ticket.due_date and ticket.status != ticket.STATUS_CLOSED:
            now = timezone.now()
            total_seconds = (ticket.due_date - ticket.created_at).total_seconds()
            elapsed_seconds = (now - ticket.created_at).total_seconds()
            if total_seconds > 0:
                sla_percent = min(100, round(elapsed_seconds / total_seconds * 100))
                if sla_percent >= 100:
                    sla_color = 'danger'
                elif sla_percent >= 75:
                    sla_color = 'warning'
                elif sla_percent >= 50:
                    sla_color = 'info'
                else:
                    sla_color = 'success'
        context['sla_percent'] = sla_percent
        context['sla_color'] = sla_color

        return context


class TicketExportCSVView(LoginRequiredMixin, View):
    """Export filtered tickets as CSV (semicolon-separated, UTF-8 BOM for Excel)."""

    def get(self, request):
        user = request.user

        if is_admin_or_dispatcher(user):
            queryset = Tickets.objects.select_related('reporter', 'technician', 'equipment')
        elif is_technician(user):
            queryset = Tickets.objects.filter(technician=user).select_related('reporter', 'technician', 'equipment')
        else:
            queryset = Tickets.objects.filter(reporter=user).select_related('reporter', 'technician', 'equipment')

        # Apply same filters as TicketListView
        status_filter = request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        priority_filter = request.GET.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)

        category_filter = request.GET.get('category')
        if category_filter:
            queryset = queryset.filter(category=category_filter)

        technician_filter = request.GET.get('technician')
        if technician_filter and is_admin_or_dispatcher(user):
            if technician_filter == 'none':
                queryset = queryset.filter(technician__isnull=True)
            else:
                queryset = queryset.filter(technician_id=technician_filter)

        search_query = request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(id__icontains=search_query)
            )

        queryset = queryset.order_by('-created_at')

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'
        response.write('\ufeff')  # UTF-8 BOM so Excel opens correctly

        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            '#', 'Тема', 'Статус', 'Приоритет', 'Категория',
            'Заявитель', 'Техник', 'Оборудование',
            'Создана', 'Срок SLA', 'Закрыта',
        ])

        status_map = dict(Tickets.STATUS_CHOICES)
        priority_map = dict(Tickets.PRIORITY_CHOICES)
        category_map = dict(Tickets.CATEGORY_CHOICES)

        for ticket in queryset:
            writer.writerow([
                ticket.pk,
                ticket.title,
                status_map.get(ticket.status, ticket.status),
                priority_map.get(ticket.priority, ticket.priority),
                category_map.get(ticket.category, ticket.category),
                (ticket.reporter.get_full_name() or ticket.reporter.username) if ticket.reporter else '',
                (ticket.technician.get_full_name() or ticket.technician.username) if ticket.technician else '',
                str(ticket.equipment) if ticket.equipment else '',
                ticket.created_at.strftime('%d.%m.%Y %H:%M') if ticket.created_at else '',
                ticket.due_date.strftime('%d.%m.%Y %H:%M') if ticket.due_date else '',
                ticket.closed_at.strftime('%d.%m.%Y %H:%M') if ticket.closed_at else '',
            ])

        return response


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Tickets
    form_class = TicketCreateForm
    template_name = 'tickets/ticket_form.html'
    success_url = reverse_lazy('ticket_list')

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(
            name__in=["admin", "dispatcher", "reporter"]
        ).exists()):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.reporter = self.request.user
        response = super().form_valid(form)
        TicketHistory.objects.create(
            ticket=self.object,
            changed_by=self.request.user,
            action=TicketHistory.ACTION_CREATED,
            new_status=self.object.status,
            comment='Заявка создана',
        )
        messages.success(self.request, f'Заявка #{self.object.pk} успешно создана.')
        return response


class TicketUpdateView(LoginRequiredMixin, UpdateView):
    model = Tickets
    form_class = TicketUpdateForm
    template_name = 'tickets/ticket_update.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("Только администратор может напрямую редактировать заявки.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Tickets.objects.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('ticket_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        old_status = form.original_status
        response = super().form_valid(form)
        new_status = self.object.status
        if old_status != new_status:
            status_display = dict(Tickets.STATUS_CHOICES)
            TicketHistory.objects.create(
                ticket=self.object,
                changed_by=self.request.user,
                action=TicketHistory.ACTION_EDITED,
                old_status=old_status,
                new_status=new_status,
                comment=f'Административное изменение: {status_display.get(old_status)} → {status_display.get(new_status)}',
            )
        messages.success(self.request, 'Заявка обновлена.')
        return response


# ---------------------------------------------------------------------------
# Ticket actions
# ---------------------------------------------------------------------------

@login_required
def assign_ticket(request, pk):
    ticket = get_object_or_404(Tickets, pk=pk)
    if not is_admin_or_dispatcher(request.user):
        raise PermissionDenied

    if request.method == 'POST':
        technician_id = request.POST.get('technician')
        technician = get_object_or_404(User, pk=technician_id)
        try:
            ticket.assign(technician, changed_by=request.user)
        except ValidationError as e:
            messages.error(request, str(e))
        else:
            messages.success(request, f'Техник {technician.get_full_name() or technician.username} назначен.')
        return redirect('ticket_detail', pk=pk)

    technicians = User.objects.filter(groups__name='technician').annotate(
        open_count=Count(
            'assigned_tickets',
            filter=Q(assigned_tickets__status__in=['new', 'assigned', 'in_progress'])
        )
    ).order_by('last_name', 'first_name', 'username')
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
        ticket.start_work(changed_by=request.user)
    except ValidationError as e:
        messages.error(request, str(e))
    else:
        messages.success(request, "Статус изменён на «В работе».")

    return redirect('ticket_detail', pk=pk)


@login_required
def close_ticket(request, pk):
    ticket = get_object_or_404(Tickets, pk=pk)
    if not (is_admin_or_dispatcher(request.user) or request.user == ticket.technician):
        raise PermissionDenied

    resolution_comment = request.POST.get('resolution_comment', '').strip()

    try:
        ticket.close(changed_by=request.user)
    except ValidationError as e:
        messages.error(request, str(e))
    else:
        if resolution_comment:
            TicketHistory.objects.create(
                ticket=ticket,
                changed_by=request.user,
                action=TicketHistory.ACTION_COMMENTED,
                comment=f'Акт выполненных работ: {resolution_comment}',
            )
        messages.success(request, "Заявка закрыта.")

    return redirect('ticket_detail', pk=pk)


@login_required
def add_comment(request, pk):
    ticket = get_object_or_404(Tickets, pk=pk)

    # Check access
    user = request.user
    if not is_admin_or_dispatcher(user):
        if is_technician(user) and ticket.technician != user:
            raise PermissionDenied
        if not is_technician(user) and ticket.reporter != user:
            raise PermissionDenied

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            comment.save()
            TicketHistory.objects.create(
                ticket=ticket,
                changed_by=request.user,
                action=TicketHistory.ACTION_COMMENTED,
                comment=f'Комментарий от {request.user.get_full_name() or request.user.username}',
            )
            messages.success(request, 'Комментарий добавлен.')

    return redirect('ticket_detail', pk=pk)


# ---------------------------------------------------------------------------
# Kanban Board
# ---------------------------------------------------------------------------

class KanbanBoardView(LoginRequiredMixin, View):
    template_name = 'tickets/kanban.html'

    def get(self, request):
        user = request.user

        if is_admin_or_dispatcher(user):
            base_qs = Tickets.objects.select_related('reporter', 'technician', 'equipment')
        elif is_technician(user):
            base_qs = Tickets.objects.filter(technician=user).select_related('reporter', 'technician', 'equipment')
        else:
            base_qs = Tickets.objects.filter(reporter=user).select_related('reporter', 'technician', 'equipment')

        # Exclude closed tickets by default (Kanban focus on active work)
        show_closed = request.GET.get('show_closed') == '1'
        if not show_closed:
            base_qs = base_qs.exclude(status='closed')

        base_qs = base_qs.order_by('priority', '-created_at')

        # Map priorities to sort order for display
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}

        def sort_tickets(qs):
            return sorted(qs, key=lambda t: (priority_order.get(t.priority, 4), t.pk))

        context = {
            'col_new': sort_tickets(base_qs.filter(status='new')),
            'col_assigned': sort_tickets(base_qs.filter(status='assigned')),
            'col_in_progress': sort_tickets(base_qs.filter(status='in_progress')),
            'col_closed': sort_tickets(base_qs.filter(status='closed')) if show_closed else [],
            'show_closed': show_closed,
            'is_admin_or_dispatcher': is_admin_or_dispatcher(user),
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SearchView(LoginRequiredMixin, ListView):
    template_name = 'tickets/search_results.html'
    context_object_name = 'results'

    def get_queryset(self):
        q = self.request.GET.get('q', '').strip()
        if not q:
            return Tickets.objects.none()

        user = self.request.user
        if is_admin_or_dispatcher(user):
            qs = Tickets.objects.all()
        elif is_technician(user):
            qs = Tickets.objects.filter(technician=user)
        else:
            qs = Tickets.objects.filter(reporter=user)

        return qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(id__icontains=q)
        ).select_related('reporter', 'technician', 'equipment').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


# ---------------------------------------------------------------------------
# Reports / Analytics
# ---------------------------------------------------------------------------

class ReportsView(LoginRequiredMixin, View):
    template_name = 'tickets/reports.html'

    def dispatch(self, request, *args, **kwargs):
        if not is_admin_or_dispatcher(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        all_tickets = Tickets.objects.all()

        # --- Summary ---
        total = all_tickets.count()
        open_count = all_tickets.exclude(status='closed').count()
        closed_total = all_tickets.filter(status='closed').count()
        closed_month = all_tickets.filter(status='closed', closed_at__gte=month_start).count()
        created_month = all_tickets.filter(created_at__gte=month_start).count()
        overdue_count = all_tickets.filter(
            due_date__lt=now,
            status__in=['new', 'assigned', 'in_progress']
        ).count()

        # --- Average resolution time ---
        avg_res_qs = all_tickets.filter(
            status='closed', closed_at__isnull=False
        ).annotate(
            res=ExpressionWrapper(F('closed_at') - F('created_at'), output_field=DurationField())
        ).aggregate(avg=Avg('res'))['avg']
        avg_resolution_hours = round(avg_res_qs.total_seconds() / 3600, 1) if avg_res_qs else None

        # --- By status ---
        status_data = {
            'labels': ['Новая', 'Назначена', 'В работе', 'Закрыта'],
            'values': [
                all_tickets.filter(status='new').count(),
                all_tickets.filter(status='assigned').count(),
                all_tickets.filter(status='in_progress').count(),
                all_tickets.filter(status='closed').count(),
            ],
            'colors': ['#ef4444', '#FF6600', '#3b82f6', '#10b981'],
        }

        # --- By category ---
        cat_counts = {c[0]: 0 for c in Tickets.CATEGORY_CHOICES}
        for row in all_tickets.values('category').annotate(cnt=Count('id')):
            cat_counts[row['category']] = row['cnt']
        category_data = {
            'labels': [c[1] for c in Tickets.CATEGORY_CHOICES],
            'values': [cat_counts[c[0]] for c in Tickets.CATEGORY_CHOICES],
            'colors': ['#6366f1', '#3b82f6', '#10b981', '#f59e0b', '#94a3b8'],
        }

        # --- By priority ---
        pri_counts = {p[0]: 0 for p in Tickets.PRIORITY_CHOICES}
        for row in all_tickets.values('priority').annotate(cnt=Count('id')):
            pri_counts[row['priority']] = row['cnt']
        priority_data = {
            'labels': [p[1] for p in Tickets.PRIORITY_CHOICES],
            'values': [pri_counts[p[0]] for p in Tickets.PRIORITY_CHOICES],
            'colors': ['#94a3b8', '#3b82f6', '#f59e0b', '#ef4444'],
        }

        # --- Tickets per day (last 30 days) ---
        start_30 = now - timedelta(days=29)
        daily_raw = (
            all_tickets.filter(created_at__gte=start_30)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(cnt=Count('id'))
            .order_by('day')
        )
        day_map = {row['day'].strftime('%d.%m'): row['cnt'] for row in daily_raw}
        labels_30 = []
        values_30 = []
        for i in range(30):
            d = (start_30 + timedelta(days=i)).date()
            key = d.strftime('%d.%m')
            labels_30.append(key)
            values_30.append(day_map.get(key, 0))

        trend_data = {'labels': labels_30, 'values': values_30}

        # --- Technician stats ---
        technicians = User.objects.filter(groups__name='technician')
        tech_stats = []
        for tech in technicians:
            qs = Tickets.objects.filter(technician=tech)
            total_t = qs.count()
            open_t = qs.exclude(status='closed').count()
            closed_t = qs.filter(status='closed').count()
            avg_t = qs.filter(status='closed', closed_at__isnull=False).annotate(
                res=ExpressionWrapper(F('closed_at') - F('created_at'), output_field=DurationField())
            ).aggregate(avg=Avg('res'))['avg']
            avg_hours = round(avg_t.total_seconds() / 3600, 1) if avg_t else None
            tech_stats.append({
                'username': tech.username,
                'full_name': tech.get_full_name() or tech.username,
                'total': total_t,
                'open': open_t,
                'closed': closed_t,
                'avg_hours': avg_hours,
            })

        # --- Recent activity ---
        recent_history = TicketHistory.objects.select_related(
            'ticket', 'changed_by'
        ).order_by('-timestamp')[:20]

        context = {
            'total': total,
            'open_count': open_count,
            'closed_total': closed_total,
            'closed_month': closed_month,
            'created_month': created_month,
            'overdue_count': overdue_count,
            'avg_resolution_hours': avg_resolution_hours,
            'status_data': json.dumps(status_data),
            'category_data': json.dumps(category_data),
            'priority_data': json.dumps(priority_data),
            'trend_data': json.dumps(trend_data),
            'tech_stats': tech_stats,
            'recent_history': recent_history,
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------

class UserProfileView(LoginRequiredMixin, View):
    template_name = 'tickets/profile.html'

    def get(self, request):
        user = request.user
        form = ProfileForm(initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        })
        reported = Tickets.objects.filter(reporter=user)
        assigned = Tickets.objects.filter(technician=user)
        context = {
            'form': form,
            'reported_total': reported.count(),
            'reported_open': reported.exclude(status='closed').count(),
            'reported_closed': reported.filter(status='closed').count(),
            'assigned_total': assigned.count(),
            'assigned_open': assigned.exclude(status='closed').count(),
            'assigned_closed': assigned.filter(status='closed').count(),
            'recent_tickets': reported.order_by('-created_at')[:5],
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = ProfileForm(request.POST)
        if form.is_valid():
            user = request.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save(update_fields=['first_name', 'last_name', 'email'])
            messages.success(request, 'Профиль обновлён.')
            return redirect('profile')

        user = request.user
        reported = Tickets.objects.filter(reporter=user)
        assigned = Tickets.objects.filter(technician=user)
        context = {
            'form': form,
            'reported_total': reported.count(),
            'reported_open': reported.exclude(status='closed').count(),
            'reported_closed': reported.filter(status='closed').count(),
            'assigned_total': assigned.count(),
            'assigned_open': assigned.exclude(status='closed').count(),
            'assigned_closed': assigned.filter(status='closed').count(),
            'recent_tickets': reported.order_by('-created_at')[:5],
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# User Registration (self-service)
# ---------------------------------------------------------------------------

class RegisterView(View):
    template_name = 'registration/register.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('ticket_list')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = UserRegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            from django.contrib.auth import login
            from django.contrib.auth.models import Group

            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1'],
                first_name=form.cleaned_data.get('first_name', ''),
                last_name=form.cleaned_data.get('last_name', ''),
                email=form.cleaned_data.get('email', ''),
            )

            # Assign reporter role by default
            reporter_group, _ = Group.objects.get_or_create(name='reporter')
            user.groups.add(reporter_group)

            login(request, user)
            messages.success(
                request,
                f'Добро пожаловать, {user.get_full_name() or user.username}! '
                'Аккаунт создан. Вы можете создавать заявки.'
            )
            return redirect('ticket_list')

        return render(request, self.template_name, {'form': form})


# ---------------------------------------------------------------------------
# User Management (admin only)
# ---------------------------------------------------------------------------

class UserManagementView(LoginRequiredMixin, ListView):
    template_name = 'tickets/user_list.html'
    context_object_name = 'users'

    def dispatch(self, request, *args, **kwargs):
        if not is_admin_or_dispatcher(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return User.objects.prefetch_related('groups').order_by('username')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Annotate each user with role and ticket counts
        user_data = []
        for u in context['users']:
            groups = [g.name for g in u.groups.all()]
            if u.is_superuser or 'admin' in groups:
                role = 'Администратор'
            elif 'dispatcher' in groups:
                role = 'Диспетчер'
            elif 'technician' in groups:
                role = 'Техник'
            else:
                role = 'Пользователь'

            user_data.append({
                'user': u,
                'role': role,
                'reported': u.reported_tickets.count(),
                'assigned': u.assigned_tickets.count(),
            })
        context['user_data'] = user_data
        return context


@login_required
def user_edit(request, pk):
    if not is_admin_or_dispatcher(request.user):
        raise PermissionDenied

    target_user = get_object_or_404(User, pk=pk)

    # Determine current role
    groups = [g.name for g in target_user.groups.all()]
    if target_user.is_superuser or 'admin' in groups:
        current_role = 'admin'
    elif 'dispatcher' in groups:
        current_role = 'dispatcher'
    elif 'technician' in groups:
        current_role = 'technician'
    else:
        current_role = 'reporter'

    if request.method == 'POST':
        form = UserEditForm(request.POST)
        if form.is_valid():
            target_user.first_name = form.cleaned_data['first_name']
            target_user.last_name = form.cleaned_data['last_name']
            target_user.email = form.cleaned_data['email']
            target_user.is_active = form.cleaned_data['is_active']
            target_user.save(update_fields=['first_name', 'last_name', 'email', 'is_active'])

            new_role = form.cleaned_data['role']
            from django.contrib.auth.models import Group
            target_user.groups.clear()
            if new_role != 'admin':
                group, _ = Group.objects.get_or_create(name=new_role)
                target_user.groups.add(group)

            messages.success(request, f'Пользователь {target_user.username} обновлён.')
            return redirect('user_list')
    else:
        form = UserEditForm(initial={
            'first_name': target_user.first_name,
            'last_name': target_user.last_name,
            'email': target_user.email,
            'role': current_role,
            'is_active': target_user.is_active,
        })

    return render(request, 'tickets/user_edit.html', {
        'form': form,
        'target_user': target_user,
    })
