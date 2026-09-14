from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.admin_overview_view, name='overview'),
    path('toggle-account-status/<int:account_id>/', views.admin_toggle_account_status_view, name='toggle_account_status'),
    path('close-fd/<int:fd_id>/', views.admin_close_fd_view, name='close_fd'),
    path('analytics-api/', views.admin_analytics_api, name='analytics_api'),
]
