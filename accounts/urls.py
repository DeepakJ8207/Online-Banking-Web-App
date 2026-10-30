from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('login/verify-otp/', views.login_otp_view, name='login_otp'),
    path('first-time-setup/', views.first_time_setup_view, name='first_time_setup'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
    path('profile/password/', views.change_password_view, name='change_password'),
    path('profile/password/forgot/', views.change_password_forgot_view, name='change_password_forgot'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('audit-logs/', views.audit_logs_view, name='audit_logs'),
    path('link-account/', views.link_account_view, name='link_account'),
    path('link-account/verify-otp/', views.link_account_otp_view, name='link_account_otp'),
    path('switch-account/<int:user_id>/', views.switch_account_view, name='switch_account'),
    path('remove-linked-account/<int:user_id>/', views.remove_linked_account_view, name='remove_linked_account'),
]
