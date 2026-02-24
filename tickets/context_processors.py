def user_role(request):
    """Context processor для определения роли пользователя"""
    context = {}
    
    if request.user.is_authenticated:
        if request.user.is_superuser:
            context['user_role'] = 'admin'
            context['user_role_display'] = 'Администратор'
            context['user_role_badge'] = 'bg-warning text-dark'
        elif request.user.groups.filter(name='dispatcher').exists():
            context['user_role'] = 'dispatcher'
            context['user_role_display'] = 'Диспетчер'
            context['user_role_badge'] = 'bg-info'
        elif request.user.groups.filter(name='technician').exists():
            context['user_role'] = 'technician'
            context['user_role_display'] = 'Техник'
            context['user_role_badge'] = 'bg-success'
        elif request.user.groups.filter(name='admin').exists():
            context['user_role'] = 'admin'
            context['user_role_display'] = 'Администратор'
            context['user_role_badge'] = 'bg-warning text-dark'
        else:
            context['user_role'] = 'reporter'
            context['user_role_display'] = 'Пользователь'
            context['user_role_badge'] = 'bg-secondary'
    
    return context