from django.db import models
from django.contrib.auth import get_user_model

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
    STATUS_CHOICES = [
        ('new', 'новая'),
        ('assigned', 'назначена'),
        ('in_progress', 'В работе'),
        ('closed', 'закрыта'),
    ]
    
    equipment = models.ForeignKey(Equipment, on_delete=models.SET_NULL, null=True)
    reporter = models.ForeignKey(User, related_name="reported_tickets", on_delete=models.SET_NULL,  null=True)
    technician = models.ForeignKey(User, related_name="assigned_tickets", on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    closed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} #{self.id}"