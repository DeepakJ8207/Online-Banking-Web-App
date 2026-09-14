from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'reference_number', 'sender_name', 'receiver_name', 'amount', 'transaction_type', 'status', 'category', 'timestamp')
    search_fields = ('transaction_id', 'reference_number', 'sender_name', 'receiver_name', 'remarks')
    list_filter = ('transaction_type', 'status', 'category', 'timestamp')
    readonly_fields = ('transaction_id', 'reference_number', 'timestamp', 'sender_balance_after', 'receiver_balance_after')
