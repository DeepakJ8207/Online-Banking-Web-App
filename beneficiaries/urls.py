from django.urls import path
from . import views

app_name = 'beneficiaries'

urlpatterns = [
    path('', views.beneficiary_list_view, name='list'),
    path('add/', views.beneficiary_add_view, name='add'),
    path('edit/<int:beneficiary_id>/', views.beneficiary_edit_view, name='edit'),
    path('delete/<int:beneficiary_id>/', views.beneficiary_delete_view, name='delete'),
]
