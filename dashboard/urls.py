from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home_view, name='home'),
    path('manager-overview/', views.admin_overview_view, name='admin_overview'),
    path('api/analytics/', views.dashboard_analytics_api, name='analytics_api'),
]
