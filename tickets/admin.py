from django.contrib import admin
from .models import Equipment, Tickets, Comment, TicketHistory


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['model', 'serial', 'location', 'status', 'purchased_at']
    list_filter = ['status']
    search_fields = ['model', 'serial', 'location']


@admin.register(Tickets)
class TicketsAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'status', 'priority', 'category', 'reporter', 'technician', 'created_at']
    list_filter = ['status', 'priority', 'category']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'closed_at']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'author', 'created_at']
    list_filter = ['created_at']


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'action', 'changed_by', 'comment', 'timestamp']
    list_filter = ['action']
    readonly_fields = ['timestamp']
