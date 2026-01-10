"""
URL configuration for home project.
"""
from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication URLs
    path('', core_views.login_view, name='home'),
    path('login/', core_views.login_view, name='login'),
    path('register/', core_views.register_view, name='register'),
    path('logout/', core_views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', core_views.dashboard_view, name='dashboard'),
    # Parent URLs
    path('parent/', include('parent.urls')),
]


# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)