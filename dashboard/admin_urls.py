from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.admin_overview_view, name='overview'),
    path('create-customer/', views.admin_create_customer_view, name='create_customer'),
    path('manage-account/<int:account_id>/', views.admin_manage_account_action_view, name='manage_account_action'),
    path('clear-all-customers/', views.admin_clear_all_customers_view, name='clear_all_customers'),
    path('toggle-account-status/<int:account_id>/', views.admin_toggle_account_status_view, name='toggle_account_status'),
    path('adjust-balance/<int:account_id>/', views.admin_adjust_balance_view, name='adjust_balance'),
    path('create-fd/', views.admin_create_fd_view, name='create_fd'),
    path('close-fd/<int:fd_id>/', views.admin_close_fd_view, name='close_fd'),
    path('create-rd/', views.admin_create_rd_view, name='create_rd'),
    path('close-rd/<int:rd_id>/', views.admin_close_rd_view, name='close_rd'),
    path('create-loan/', views.admin_create_loan_view, name='create_loan'),
    path('close-loan/<int:loan_id>/', views.admin_close_loan_view, name='close_loan'),
    path('analytics-api/', views.admin_analytics_api, name='analytics_api'),
]
