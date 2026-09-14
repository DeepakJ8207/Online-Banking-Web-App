from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.finance_home_view, name='home'),
    path('emi/', views.emi_calculator_view, name='emi_calculator'),
    path('fd/', views.fd_calculator_view, name='fd_calculator'),
    path('rd/', views.rd_calculator_view, name='rd_calculator'),
    path('sip/', views.sip_calculator_view, name='sip_calculator'),
    path('loans/', views.loans_list_view, name='loans'),
    path('loans/apply/', views.loan_apply_view, name='loan_apply'),
    path('loans/<int:loan_id>/', views.loan_detail_view, name='loan_detail'),
    path('loans/<int:loan_id>/pay-emi/', views.loan_pay_emi_view, name='loan_pay_emi'),
    path('deposits/', views.deposits_view, name='deposits'),
    path('deposits/open-fd/', views.open_fd_view, name='open_fd'),
    path('deposits/fd-receipt/<int:fd_id>/', views.fd_receipt_view, name='fd_receipt'),
    path('deposits/open-rd/', views.open_rd_view, name='open_rd'),
    path('deposits/rd-receipt/<int:rd_id>/', views.rd_receipt_view, name='rd_receipt'),
]
