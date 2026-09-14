from django.urls import path
from . import views

app_name = 'bills'

urlpatterns = [
    path('', views.bills_home_view, name='home'),
    path('pay/', views.pay_bill_view, name='pay'),
    path('pay/<str:category_code>/', views.pay_bill_view, name='pay_category'),
    path('receipt/<str:receipt_number>/', views.bill_receipt_view, name='receipt'),
]
