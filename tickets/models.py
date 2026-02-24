from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()


class Equipment(models.Model):
    STATUS_IN_USE = 'in_use'
    STATUS_IN_REPAIR = 'in_repair'
    STATUS_STORAGE = 'storage'

    STATUS_CHOICES = [
        (STATUS_IN_USE, 'В использовании'),
        (STATUS_IN_REPAIR, 'В ремонте'),
        (STATUS_STORAGE, 'На складе'),
    ]

    serial = models.CharField(max_length=100, unique=True, verbose_name='Серийный номер')
    model = models.CharField(max_length=200, verbose_name='Модель')
    location = models.CharField(max_length=200, blank=True, verbose_name='Расположение')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IN_USE,
        verbose_name='Статус'
    )
    purchased_at = models.DateField(null=True, blank=True, verbose_name='Дата приобретения')
    notes = models.TextField(blank=True, verbose_name='Примечания')

    class Meta:
        verbose_name = 'Оборудование'
        verbose_name_plural = 'Оборудование'
        ordering = ['model']

    def __str__(self):
        return f"{self.model} ({self.serial})"


class Tickets(models.Model):
    STATUS_NEW = 'new'
    STATUS_ASSIGNED = 'assigned'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = [
        (STATUS_NEW, 'Новая'),
        (STATUS_ASSIGNED, 'Назначена'),
        (STATUS_IN_PROGRESS, 'В работе'),
        (STATUS_CLOSED, 'Закрыта'),
    ]

    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CRITICAL = 'critical'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Низкий'),
        (PRIORITY_MEDIUM, 'Средний'),
        (PRIORITY_HIGH, 'Высокий'),
        (PRIORITY_CRITICAL, 'Критический'),
    ]

    CATEGORY_HARDWARE = 'hardware'
    CATEGORY_SOFTWARE = 'software'
    CATEGORY_NETWORK = 'network'
    CATEGORY_PRINTER = 'printer'
    CATEGORY_OTHER = 'other'

    CATEGORY_CHOICES = [
        (CATEGORY_HARDWARE, 'Железо'),
        (CATEGORY_SOFTWARE, 'Программное обеспечение'),
        (CATEGORY_NETWORK, 'Сеть'),
        (CATEGORY_PRINTER, 'Принтер / МФУ'),
        (CATEGORY_OTHER, 'Другое'),
    ]

    ALLOWED_TRANSITIONS = {
        STATUS_NEW: [STATUS_ASSIGNED, STATUS_CLOSED],
        STATUS_ASSIGNED: [STATUS_IN_PROGRESS, STATUS_CLOSED],
        STATUS_IN_PROGRESS: [STATUS_CLOSED],
        STATUS_CLOSED: [],
    }

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        verbose_name='Оборудование'
    )
    reporter = models.ForeignKey(
        User,
        related_name='reported_tickets',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Заявитель'
    )
    technician = models.ForeignKey(
        User,
        related_name='assigned_tickets',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Техник'
    )
    title = models.CharField(max_length=255, verbose_name='Тема')
    description = models.TextField(verbose_name='Описание')
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM,
        verbose_name='Приоритет'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_OTHER,
        verbose_name='Категория'
    )
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Срок выполнения (SLA)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        verbose_name='Статус'
    )
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Закрыта')

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']
        permissions = [
            ('can_assign_ticket', 'Can assign ticket'),
            ('can_create_ticket', 'Can create ticket'),
            ('can_change_status', 'Can change ticket status'),
        ]

    def assign(self, technician, changed_by=None, bypass_validation=False):
        if not technician:
            raise ValidationError("Не указан техник")

        self.technician = technician
        self.change_status(self.STATUS_ASSIGNED, changed_by=changed_by, bypass_validation=bypass_validation)
        self.save(update_fields=['technician', 'status', 'closed_at'])

        TicketHistory.objects.create(
            ticket=self,
            changed_by=changed_by,
            action=TicketHistory.ACTION_ASSIGNED,
            comment=f'Назначен техник: {technician.get_full_name() or technician.username}',
        )

    def start_work(self, changed_by=None, bypass_validation=False):
        if not self.technician:
            raise ValidationError("Нельзя начать работу без техника")
        self.change_status(self.STATUS_IN_PROGRESS, changed_by=changed_by, bypass_validation=bypass_validation)

    def change_status(self, new_status, changed_by=None, bypass_validation=False):
        old_status = self.status

        if not bypass_validation:
            allowed = self.ALLOWED_TRANSITIONS.get(self.status, [])
            if new_status not in allowed:
                raise ValidationError(
                    f"Недопустимый переход: {self.status} → {new_status}"
                )

        self.status = new_status

        if new_status == self.STATUS_CLOSED and self.closed_at is None:
            self.closed_at = timezone.now()

        self.save()

        if old_status != new_status:
            status_display = dict(self.STATUS_CHOICES)
            TicketHistory.objects.create(
                ticket=self,
                changed_by=changed_by,
                action=TicketHistory.ACTION_STATUS_CHANGED,
                old_status=old_status,
                new_status=new_status,
                comment=f'{status_display.get(old_status, old_status)} → {status_display.get(new_status, new_status)}',
            )

    def close(self, changed_by=None, bypass_validation=False):
        self.change_status(self.STATUS_CLOSED, changed_by=changed_by, bypass_validation=bypass_validation)

    def is_overdue(self):
        if self.due_date and self.status != self.STATUS_CLOSED:
            return timezone.now() > self.due_date
        return False

    def resolution_hours(self):
        if self.closed_at:
            delta = self.closed_at - self.created_at
            return round(delta.total_seconds() / 3600, 1)
        return None

    def __str__(self):
        return f"{self.title} #{self.pk}"


class Comment(models.Model):
    ticket = models.ForeignKey(
        Tickets,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Заявка'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Автор'
    )
    text = models.TextField(verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['created_at']

    def __str__(self):
        return f"Комментарий от {self.author} к #{self.ticket.pk}"


class TicketHistory(models.Model):
    ACTION_CREATED = 'created'
    ACTION_STATUS_CHANGED = 'status_changed'
    ACTION_ASSIGNED = 'assigned'
    ACTION_COMMENTED = 'commented'
    ACTION_EDITED = 'edited'

    ACTION_CHOICES = [
        (ACTION_CREATED, 'Создана'),
        (ACTION_STATUS_CHANGED, 'Статус изменён'),
        (ACTION_ASSIGNED, 'Назначен техник'),
        (ACTION_COMMENTED, 'Добавлен комментарий'),
        (ACTION_EDITED, 'Отредактирована'),
    ]

    ticket = models.ForeignKey(
        Tickets,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='Заявка'
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Изменил'
    )
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        default=ACTION_STATUS_CHANGED,
        verbose_name='Действие'
    )
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    comment = models.TextField(blank=True, verbose_name='Описание')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'История заявки'
        verbose_name_plural = 'История заявок'
        ordering = ['timestamp']

    def __str__(self):
        return f"История #{self.ticket.pk} — {self.get_action_display()}"
