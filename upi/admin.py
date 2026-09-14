from django.contrib import admin
from .models import UPIAccount, UPITransaction

@admin.register(UPIAccount)
class UPIAccountAdmin(admin.ModelAdmin):
    list_display = ('upi_id', 'user', 'bank_account', 'is_primary', 'is_active', 'daily_limit', 'created_at')
    search_fields = ('upi_id', 'user__username', 'bank_account__account_number')
    list_filter = ('is_primary', 'is_active')

@admin.register(UPITransaction)
class UPITransactionAdmin(admin.ModelAdmin):
    list_display = ('sender_upi_id', 'receiver_upi_id', 'transaction', 'npci_simulated_ref', 'created_at')
    search_fields = ('sender_upi_id', 'receiver_upi_id', 'npci_simulated_ref')
