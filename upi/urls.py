from django.urls import path
from . import views

app_name = 'upi'

urlpatterns = [
    path('', views.upi_home_view, name='home'),
    path('create/', views.create_upi_view, name='create'),
    path('qr/<str:upi_id>/', views.upi_qr_view, name='qr_code'),
    path('qr/<str:upi_id>/image/', views.upi_qr_image_view, name='qr_image'),
    path('pin/<str:upi_id>/', views.change_upi_pin_view, name='change_pin'),
    path('pin/<str:upi_id>/forgot/', views.forgot_upi_pin_view, name='forgot_pin'),
]
