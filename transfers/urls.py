from django.urls import path
from . import views

app_name = 'transfers'

urlpatterns = [
    path('', views.transfer_home_view, name='home'),
    path('bank/', views.bank_transfer_view, name='bank_transfer'),
    path('mobile/', views.mobile_transfer_view, name='mobile_transfer'),
    path('upi/', views.upi_transfer_view, name='upi_transfer'),
    path('self/', views.self_transfer_view, name='self_transfer'),
    path('receipt/<str:transaction_id>/', views.transfer_receipt_view, name='receipt'),
]
