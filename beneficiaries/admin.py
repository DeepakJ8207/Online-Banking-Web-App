from django.contrib import admin
from .models import Beneficiary

@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ('beneficiary_name', 'user', 'account_number', 'ifsc_code', 'bank_name', 'nickname', 'is_active', 'created_at')
    search_fields = ('beneficiary_name', 'account_number', 'user__username', 'ifsc_code', 'bank_name')
    list_filter = ('bank_name', 'is_active')
