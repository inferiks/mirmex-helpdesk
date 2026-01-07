from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils import timezone
from django.core.exceptions import ValidationError
User = get_user_model()

class Equipment(models.Model):
    serial = models.CharField(max_length=100, unique=True)
    model = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('in_use', 'В использовании'),
            ('in_repair', 'в ремонте'),
            ('sorage', 'на складе')
        ],
        default='in_use'
    )
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
        related_name='tickets'
    )
    reporter = models.ForeignKey(
        User,
        related_name='reported_tickets',
        on_delete=models.SET_NULL,
        null=True
    )
    technician = models.ForeignKey(
        User,
        related_name='assigned_tickets',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    title = models.CharField(max_length=255)
    description = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        permissions = [
            ('can_assign_ticket', 'Can assign ticket'),
            ('can_create_ticket', 'Can create ticket'),
            ('can_change_status', 'Can change ticket status'),
        ]

    def assign(self, technician):
        if not technician:
            raise ValidationError("Не указан техник")
        
        self.technician = technician
        self.change_status(self.STATUS_ASSIGNED)
        self.save(update_fields=['technician', 'status', 'closed_at'])

        
    def start_work(self):
        if not self.technician:
            raise ValidationError("Нельзя начать работу без техника")
        
        self.change_status(self.STATUS_IN_PROGRESS)

    def change_status(self, new_status):
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValidationError(
                f"недопустимый переход: {self.status} → {new_status}"
            )
            
        self.status = new_status
        
        if new_status == self.STATUS_CLOSED and self.closed_at is None:
            self.closed_at = timezone.now()


        self.save()

    def close(self):
        self.change_status(self.STATUS_CLOSED)

    def __str__(self):
        return f"{self.title} #{self.pk}"
