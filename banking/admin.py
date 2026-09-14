from django.contrib import admin
from .models import BankAccount, AccountStatementRequest

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'account_type', 'branch', 'balance', 'status', 'opening_date')
    search_fields = ('account_number', 'user__username', 'user__first_name', 'user__last_name')
    list_filter = ('account_type', 'status', 'branch')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(AccountStatementRequest)
class AccountStatementRequestAdmin(admin.ModelAdmin):
    list_display = ('account', 'user', 'start_date', 'end_date', 'created_at')
    search_fields = ('account__account_number', 'user__username')
