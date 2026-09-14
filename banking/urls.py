from django.urls import path
from . import views

app_name = 'banking'

urlpatterns = [
    path('', views.my_account_view, name='my_account'),
    path('<int:account_id>/', views.account_details_view, name='account_details'),
    path('<int:account_id>/change-pin/', views.change_pin_view, name='change_pin'),
]
