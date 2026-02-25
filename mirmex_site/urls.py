"""
URL configuration for mirmex_site project.
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from tickets.views import RegisterView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url='/tickets/', permanent=False)),
    path("", include('tickets.urls')),

    # Authentication
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', RegisterView.as_view(), name='register'),

    # Password change (built-in views with custom templates)
    path(
        'accounts/password_change/',
        auth_views.PasswordChangeView.as_view(
            template_name='registration/password_change.html',
            success_url='/profile/',
        ),
        name='password_change',
    ),
    path(
        'accounts/password_change/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='registration/password_change_done.html',
        ),
        name='password_change_done',
    ),
]

# Custom error handlers
handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
