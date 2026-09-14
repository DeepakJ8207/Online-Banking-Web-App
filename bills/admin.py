from django.contrib import admin
from .models import BillerCategory, Biller, BillPayment

@admin.register(BillerCategory)
class BillerCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'icon')

@admin.register(Biller)
class BillerAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'service_area', 'consumer_label', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'service_area')

@admin.register(BillPayment)
class BillPaymentAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'user', 'biller', 'consumer_number', 'amount', 'biller_status', 'payment_date')
    search_fields = ('receipt_number', 'consumer_number', 'user__username', 'biller__name')
    list_filter = ('biller_status', 'biller__category', 'payment_date')
    readonly_fields = ('receipt_number', 'payment_date')
