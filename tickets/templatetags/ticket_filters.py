from django import template

register = template.Library()

@register.filter
def filter_status(queryset, status):
    """Фильтр для подсчёта заявок по статусу"""
    return queryset.filter(status=status)