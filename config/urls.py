"""
URL configuration for Prime Reserve Bank Online Banking Web Application.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

def custom_404_view(request, exception=None):
    return render(request, '404.html', status=404)

def custom_403_view(request, exception=None):
    return render(request, '403.html', status=403)

def custom_500_view(request):
    return render(request, '500.html', status=500)

handler404 = custom_404_view
handler403 = custom_403_view
handler500 = custom_500_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-dashboard/', include('dashboard.admin_urls')),
    path('', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('account/', include('banking.urls')),
    path('transfers/', include('transfers.urls')),
    path('beneficiaries/', include('beneficiaries.urls')),
    path('transactions/', include('transactions.urls')),
    path('bills/', include('bills.urls')),
    path('upi/', include('upi.urls')),
    path('finance/', include('finance.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site branding
admin.site.site_header = "PRIME RESERVE BANK — Core Banking Administration"
admin.site.site_title = "PRMB Core Banking Admin"
admin.site.index_title = "System Management & Database Administration"
