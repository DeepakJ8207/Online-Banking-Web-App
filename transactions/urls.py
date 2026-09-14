from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.transaction_history_view, name='history'),
    path('statement/download/', views.download_statement_pdf_view, name='download_statement'),
    path('<str:transaction_id>/', views.transaction_detail_view, name='detail'),
]
